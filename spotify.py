from typing import Dict

import requests

from config import SPOTIFY_API_BASE_URL


def get_current_playing(access_token: str) -> Dict[str, str | bool | int]  | None:
    if not access_token:
        return {"error": "Access code not found", "status_code": 401}

    try:
        # Fetch currently playing track
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            f"{SPOTIFY_API_BASE_URL}/me/player/currently-playing",
            headers=headers
        )

        if response.status_code == 204:
            return {"is_playing": False, "message": "No track is currently playing"}

        elif response.status_code == 200:
            return response.json()

        else:
            response.raise_for_status()

    except Exception as e:
        return {"error": str(e), "status_code": response.status_code, "message": response.reason}