import os
import secrets
import base64
import requests
import time
import redis

from dotenv import load_dotenv

from fastapi import FastAPI, Request, HTTPException, status
# from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from urllib.parse import urlencode

# Load environment variables from .env file FIRST
load_dotenv()

# --- Spotify API Configuration ---
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
# SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", secrets.token_urlsafe(32))

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")


# Spotify API Endpoints - CORRECTED URLs
# These were the main cause of your "INVALID_CLIENT" error if the redirect URI itself was correct.
# The previous URLs were placeholders (e.g., https://accounts.spotify.com/authorize) and not actual Spotify endpoints.
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"


app = FastAPI()
# app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)


redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, db=0, decode_responses=True)

# states = {}


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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="State not recognized. Possible CSRF attack detected")
    
    # Clean up the state from Redis
    redis_client.delete(f"spotify_state:{state}")

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    headers = {
        'content-type': 'application/x-www-form-urlencoded',
        'Authorization': 'Basic ' + base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode('utf-8')
    }

    # Getting access token
    response = requests.post(SPOTIFY_TOKEN_URL, data=data, headers=headers)
    if not response.ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to obtain access token")
    
    access_token = response.json().get("access_token", None)
    refresh_token = response.json().get("refresh_token", None)

    if not access_token or not refresh_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Access token not found in response")
    
    # request.session['access_token'] = access_token
    # request.session['refresh_token'] = refresh_token
    # return RedirectResponse(url="/")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


@app.get("/refresh_token")
def refresh_token(refresh_token: str | None = None, access_token: str | None = None):
    # refresh_token = request.session.get('refresh_token', None)
    # access_token = request.session.get('access_token', None)


    if not refresh_token or not access_token:
        return RedirectResponse(url="/authorize")

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic " + base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode('utf-8')
    }

    response = requests.post(SPOTIFY_TOKEN_URL, data=data, headers=headers)
    if not response.status_code == 200:
        return {"error": "Failed to refresh token"}
    
    new_access_token = response.json().get("access_token", None)
    if not new_access_token:
        return {"error": "New access token not found in response"}

    # request.session['access_token'] = new_access_token
    return {"access_token": new_access_token}


@app.get("/")
def current_playing(access_token: str | None = None):
    # access_token = request.session.get('access_token', None)
    if not access_token:
        return RedirectResponse(url="/authorize")
    
    # Fetch currently playing track
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(f"{SPOTIFY_API_BASE_URL}/me/player/currently-playing", headers=headers)

    if response.status_code == 204:
        return {"is_playing": False, "message": "No track is currently playing"}

    elif response.status_code == 200:
        return response.json()

    elif access_token and response.status_code == 401:
        return RedirectResponse(url="/refresh_token")

    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching data from Spotify")