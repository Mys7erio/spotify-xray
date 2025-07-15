import asyncio
import json
import logging
import time
from typing import Any, Dict

import redis
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from config import GLOBAL_LOG_LEVEL, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT
from exceptions import InternalServerError
from spotify import (
    auth_using_spotify,
    get_access_and_refresh_tokens,
    get_current_playing,
    refresh_access_token,
)
from utils import get_song_duration, get_song_progress, is_song_playing
from xray import get_song_info

logging.basicConfig(level=GLOBAL_LOG_LEVEL)
logger = logging.getLogger(__name__)

from urllib.parse import urlencode

app = FastAPI()
start_time = time.time()

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    db=0,
    decode_responses=True,
)


@app.get("/authorize")
def authorize():
    redirect_url = auth_using_spotify(redis_client)
    response = RedirectResponse(url=redirect_url)
    return response


@app.get("/home")
def home(request: Request):
    try:
        code = request.query_params.get("code")
        state = request.query_params.get("state")

        if not state or not code:
            raise InternalServerError("Missing state or code parameter in request")

        return get_access_and_refresh_tokens(redis_client, code, state)

    except Exception as e:
        logger.error(f"Error getting access code: {e}")
        return {"error": str(e)}


@app.get("/refresh_token")
def refresh_token(refresh_token: str):
    try:
        return refresh_access_token(refresh_token)
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        return {"error": str(e)}


@app.get("/livez")
def current_playing():
    return {"uptime": time.time() - start_time}


def smart_poll(song_info: Dict[str, Any]) -> float:
    try:
        if not is_song_playing(song_info):
            return 5

        # Song duration and progress in ms
        song_duration = get_song_duration(song_info)
        song_progress = get_song_progress(song_info)

        sleep_duration = (song_duration - song_progress) / 1000  # Convert to seconds
        sleep_duration /= 10  # Poll every 10% of the song duration
        sleep_duration = max(5, sleep_duration)  # Ensure at least 5 seconds delay
        logger.info(f"Updated smart poll delay: {sleep_duration}s")
        return sleep_duration

    except Exception as e:
        logger.error(f"Error in smart_poll: {e}")
        return 5  # Default poll delay in seconds


@app.get("/xray")
async def xray(access_token: str): 
    if not access_token:
        return {"error": "Access code not found", "status_code": 401}
    
    async def event_stream():
        poll_delay = 5
        while True:
            try:
                song_info = get_current_playing(access_token)
                logger.debug(f"Current song info: {song_info}")
                if not song_info:
                    yield "event: error\ndata: A Server Side Error Occured: Empty song_info\n\n"
                    await asyncio.sleep(poll_delay)
                    continue

                song_xray = get_song_info(redis_client, song_info)
                logger.info(f"X-Ray Meaning Len: {len(song_xray['meaning'])}")
                logger.info(f"X-Ray Facts Len: {len(song_xray['facts'])}")
                data = song_info | song_xray
                response = f"data: {json.dumps(data)}\n\n"

                # Update poll delay based on song progress, if everything is fine
                poll_delay = smart_poll(song_info)
                yield response

            except Exception as e:
                logger.error(f"An Unknown Error Occurred: {str(e)}")
                yield f"event: error\ndata: {str(e)}\n\n"

            finally:
                await asyncio.sleep(poll_delay)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


app.mount("/", StaticFiles(directory="static", html=True), name="home")
