import base64
import secrets
import time
from typing import Any, Dict
from urllib.parse import urlencode

import redis
import requests

from config import (
    CLIENT_ID,
    CLIENT_SECRET,
    REDIRECT_URI,
    SPOTIFY_API_BASE_URL,
    SPOTIFY_AUTH_URL,
    SPOTIFY_TOKEN_URL,
)
from exceptions import InternalServerError, StateMismatchException


def auth_using_spotify(redis_client: redis.Redis) -> str:
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
    return redirect_url


def get_access_and_refresh_tokens(
    redis_client: redis.Redis, code: str, state: str
) -> Dict[str, str]:
    # Verify the state parameter to prevent CSRF attacks
    if not redis_client.exists(f"spotify_state:{state}"):
        raise StateMismatchException("State parameter mismatch. Possible CSRF attack.")

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
        raise InternalServerError("Failed to obtain access token")

    access_token = response.json().get("access_token")
    refresh_token = response.json().get("refresh_token")

    if not access_token or not refresh_token:
        raise InternalServerError("Access token or refresh token not found in response")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


def refresh_access_token(refresh_token: str) -> Dict[str, str]:
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


def get_current_playing(access_token: str) -> Dict[str, Any] | None:
    # Fetch currently playing track
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        f"{SPOTIFY_API_BASE_URL}/me/player/currently-playing", headers=headers
    )
    if response.status_code == 204:
        return {"is_playing": False, "message": "No track is currently playing"}

    elif response.status_code == 200:
        return response.json()

    else:
        response.raise_for_status()

