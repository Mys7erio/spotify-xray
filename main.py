import asyncio
import base64
import json
import logging
import secrets
import time

import redis
import requests
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse, StreamingResponse

from spotify import get_current_playing
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


@app.get("/")
def current_playing():
    return {"uptime": time.time() - start_time}


@app.get("/xray")
async def xray(access_token: str, request: Request):
    async def event_stream():
        while True:
            try:
                song_info = get_current_playing(access_token)
                response = f"data: {json.dumps(song_info)}\n\n"
                yield response

            except Exception as e:
                yield f"event: error\ndata: {str(e)}\n\n"
                breakpoint()
            finally:
                await asyncio.sleep(5)


    return StreamingResponse(event_stream(), media_type="text/event-stream")
