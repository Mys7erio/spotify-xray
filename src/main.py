import asyncio
import json
import logging
import time

import redis
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from uuid import uuid4

from config import GLOBAL_LOG_LEVEL, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT
from exceptions import InternalServerError, ExpiredTokenException
from spotify import (
    auth_using_spotify,
    get_access_and_refresh_tokens,
    get_current_playing,
    get_current_user_uri,
    refresh_access_token,
)
from utils import Dict2EventSourceString, get_access_token, get_refresh_token, smart_poll
from xray import get_song_info

logging.basicConfig(level=GLOBAL_LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI()
start_time = time.time()

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    db=0,
    decode_responses=True,
)


@app.get("/livez")
def livez():
    return {"uptime": time.time() - start_time}


@app.get("/authorize")
def authorize():
    redirect_url = auth_using_spotify(redis_client)
    response = RedirectResponse(url=redirect_url)
    return response


@app.get("/callback")
def get_tokens(request: Request):
    try:
        code = request.query_params.get("code")
        state = request.query_params.get("state")

        if not state or not code:
            raise InternalServerError("Missing state or code parameter in request")

        access_token, refresh_token = get_access_and_refresh_tokens(redis_client, code, state)
        session_id = uuid4().hex

        redis_client.set(f"access_token:{session_id}", access_token, ex=60 * 60)  # Store access token for 60 minutes
        redis_client.set(f"refresh_token:{session_id}", refresh_token, ex=30 * 24 * 60 * 60)  # Store refresh token for 30 days

        home_page_redirect = RedirectResponse(url="/")
        # home_page_redirect.set_cookie(key="access_token", value=access_token)
        home_page_redirect.set_cookie(key="SESSIONID", value=session_id)
        return home_page_redirect

    except Exception as e:
        logger.error(f"Error getting access code: {e}")
        return {"error": str(e)}


@app.get("/refresh_token")
def refresh_token(request: Request):
    try:
        session_id = request.cookies.get("SESSIONID")
        result = refresh_access_token(redis_client, session_id)

        if "access_token" in result:
            return {"result": "success", "message": "Access token refreshed successfully"}
        else:
            return {"result": "error", "message": result.get("error", "Failed to refresh access token")}

    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        return {"error": str(e)}


@app.get("/xray")
async def xray(request: Request): 
    async def event_stream():
        POLL_DELAY = 5
        while True:
            try:
                session_id = request.cookies.get("SESSIONID")
                if not session_id:
                    message = {"status_code": 401, "message": "Session ID not found in cookies"}
                    yield Dict2EventSourceString("error", message)
                    continue
                
                refresh_token = get_refresh_token(redis_client, session_id)
                if not refresh_token:
                    message = {"status_code": 401, "message": "Refresh token not found"}
                    yield Dict2EventSourceString("error", message)
                    continue

                access_token = get_access_token(redis_client, session_id)
                logger.debug(f"Access Token: {access_token}")

                if refresh_token and not access_token:
                    access_token = refresh_access_token(redis_client, session_id).get("access_token")
                    continue

                song_info = get_current_playing(access_token)
                logger.debug(f"Current song info: {song_info}")
                if not song_info:
                    message = {"data": "A Server Side Error Occured: Empty song_info"}
                    yield Dict2EventSourceString("error", message)
                    await asyncio.sleep(POLL_DELAY)
                    continue

                if not song_info["is_playing"]:
                    yield f"data: {json.dumps(song_info)}\n\n"
                    await asyncio.sleep(POLL_DELAY) 
                    continue

                song_xray = get_song_info(redis_client, song_info)
                logger.info(f"X-Ray Meaning Len: {len(song_xray['meaning'])}")
                logger.info(f"X-Ray Facts Len: {len(song_xray['facts'])}")
                data = song_info | song_xray
                response = f"data: {json.dumps(data)}\n\n"

                # Update poll delay based on song progress, if everything is fine
                POLL_DELAY = smart_poll(song_info)
                yield response

            except ExpiredTokenException:
                logger.warning("Access token expired, attempting to refresh")
                refresh_token = get_refresh_token(redis_client, str(session_id))
                response = refresh_access_token(redis_client, str(refresh_token))

                if "access_token" in response:
                    access_token = response["access_token"]
                    redis_client.set(f"access_token:{session_id}", access_token, ex=60 * 60)

            except Exception as e:
                logger.error(f"An Unknown Error Occurred: {str(e)}")
                yield f"event: error\ndata: {str(e)}\n\n"

            finally:
                await asyncio.sleep(POLL_DELAY)

    return StreamingResponse(event_stream(), media_type="text/event-stream")



@app.get("/current_user_id")
def get_user_uri(request: Request):
    # access_token = request.cookies.get("access_token")
    session_id = request.cookies.get("SESSIONID")
    access_token = get_access_token(redis_client, session_id)
    if not access_token:
        return {"error": "Access token not found", "status_code": 401}

    try:
        user_uri = get_current_user_uri(access_token)
        return {"data": user_uri}
    except Exception as e:
        logger.error(str(e))
        return {"error": str(e)}



app.mount("/", StaticFiles(directory="static", html=True), name="home")



