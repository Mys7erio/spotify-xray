import asyncio
import base64
import json
import logging
import secrets
import time
from typing import Any, Dict

import redis
import requests
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from spotify import get_current_playing
from utils import get_artists, get_song_duration, get_song_id, get_song_name, get_song_progress, is_song_playing
from xray import get_song_info
from config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SPOTIFY_AUTH_URL, SPOTIFY_TOKEN_URL

logging.basicConfig(level=logging.INFO)
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
    state = secrets.token_urlsafe(16)
    redis_client.set(f"spotify_state:{state}", time.time(), ex=300)

    query_params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "scope": "user-read-currently-playing",
        "redirect_uri": REDIRECT_URI,
        "state": state,
    }

    redirect_url = f"{SPOTIFY_AUTH_URL}?{urlencode(query_params)}"
    response = RedirectResponse(url=redirect_url)
    return response


@app.get("/home")
def home(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not state or not code:
        return RedirectResponse(url="/authorize")

    # Verify the state parameter to prevent CSRF attacks
    if not redis_client.exists(f"spotify_state:{state}"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State not recognized. Possible CSRF attack detected",
        )

    # Clean up the state from Redis
    redis_client.delete(f"spotify_state:{state}")

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    headers = {
        "content-type": "application/x-www-form-urlencoded",
        "Authorization": "Basic "
        + base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode("utf-8"),
    }

    # Getting access token
    response = requests.post(SPOTIFY_TOKEN_URL, data=data, headers=headers)
    if not response.ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to obtain access token",
        )

    access_token = response.json().get("access_token", None)
    refresh_token = response.json().get("refresh_token", None)

    if not access_token or not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access token not found in response",
        )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


@app.get("/refresh_token")
def refresh_token(refresh_token: str | None = None, access_token: str | None = None):
    if not refresh_token or not access_token:
        return RedirectResponse(url="/authorize")

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic "
        + base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode("utf-8"),
    }

    response = requests.post(SPOTIFY_TOKEN_URL, data=data, headers=headers)
    if not response.status_code == 200:
        return {"error": "Failed to refresh token"}

    new_access_token = response.json().get("access_token", None)
    if not new_access_token:
        return {"error": "New access token not found in response"}

    return {"access_token": new_access_token}


# @app.get("/")
# def current_playing():
#     return {"uptime": time.time() - start_time}


def smart_poll(song_info: Dict[str, Any]) -> float:
    try:
        if not is_song_playing(song_info):
            return 5
        
        song_duration_ms = get_song_duration(song_info)
        song_progress_ms = get_song_progress(song_info)

        sleep_duration = (song_duration_ms - song_progress_ms) / 1000 # Conver to seconds
        sleep_duration /= 10 # Poll every 10% of the song duration
        return max(5, sleep_duration)  # Ensure at least 5 seconds delay

    except Exception as e:
        logger.error(f"Error in smart_poll: {e}")
        return 5 # Default poll delay in seconds


async def song_changed(access_token: str, song_info: Dict[str, Any]) -> bool:
    current_song_id = redis_client.get(f"song_id:{access_token}")
    if current_song_id is None:
        return True
    
    new_song_id = get_song_id(song_info)
    current_song_id = current_song_id.split(":")[-1]

    return new_song_id != current_song_id


@app.get("/xray")
async def xray(access_token: str, request: Request):
    async def event_stream():
        poll_delay = 5
        while True:
            try:
                song_info = get_current_playing(access_token)
                if not song_info:
                    yield "event: error\ndata: A Server Side Error Occured\n\n"
                    await asyncio.sleep(poll_delay)
                    continue

                song_xray = get_song_info(redis_client, song_info)
                data = song_info | song_xray
                response = f"data: {json.dumps(data)}\n\n"

                poll_delay = smart_poll(song_info)
                yield response

                # song_did_change = await song_changed(access_token, song_info)
                # if song_did_change and is_song_playing(song_info):
                # if is_song_playing(song_info):
                    # song_id = get_song_id(song_info)
                    # Update Redis with the currently playing song ID
                    # redis_client.set(f"song_id:{access_token}", song_id)
                    # song_xray = get_song_info(redis_client, song_info)
                # else:
                #     song_xray = {}



            except Exception as e:
                breakpoint()
                print(f"Error: {e}")
                yield f"event: error\ndata: {str(e)}\n\n"

            finally:
                await asyncio.sleep(poll_delay)


    return StreamingResponse(event_stream(), media_type="text/event-stream")



app.mount("/", StaticFiles(directory="static", html=True), name="home")
