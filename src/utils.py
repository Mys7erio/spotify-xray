from typing import Any, Dict, List, Literal, Tuple
import logging

import redis

from config import GLOBAL_LOG_LEVEL

logging.basicConfig(level=GLOBAL_LOG_LEVEL)
logger = logging.getLogger(__name__)


def get_artists(song_info: Dict[str, Any]) -> Tuple[str, List[str]]:
    artists = [artist_info["name"] for artist_info in song_info["item"]["artists"]]
    artist_names = ", ".join(artists)

    return artist_names, artists


def get_song_id(song_info: Dict[str, Any]) -> str:
    return song_info["item"]["id"]


def get_song_name(song_info: Dict[str, Any]) -> str:
    return song_info["item"]["name"]


def get_album_name(song_info: Dict[str, Any]) -> str:
    return song_info["item"]["album"]["name"]


def get_song_duration(song_info: Dict[str, Any]) -> int:
    return song_info["item"]["duration_ms"]


def get_song_progress(song_info: Dict[str, Any]) -> int:
    return song_info["progress_ms"]


def is_song_playing(song_info: Dict[str, Any]) -> bool:
    return song_info["is_playing"]


def get_access_token(redis_client: redis.Redis, session_id: str) -> str | None:
    access_token = redis_client.get(f"access_token:{session_id}")
    return access_token # type: ignore


def get_refresh_token(redis_client: redis.Redis, session_id: str) -> str | None:
    refresh_token = redis_client.get(f"refresh_token:{session_id}")
    return refresh_token # type: ignore


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


def Dict2EventSourceString(event_type: Literal["data", "error"], data: Dict[str, Any]) -> str:
    response = ""
    response += f"event: {event_type}\n"
    for key, value in data.items():
        response += f"{key}: {value}\n"

    response += "\n\n"
    return response