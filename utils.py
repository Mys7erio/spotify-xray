from typing import Dict, Any, Tuple, List

def get_artists(song_info: Dict[str, Any]) -> Tuple[str, List[str]]:
    artists = [artist_info['name'] for artist_info in song_info['item']['artists']]
    artist_names = ", ".join(artists)

    return artist_names, artists
    
    

def get_song_id(song_info: Dict[str, Any]) -> str:
    return song_info['item']['id']


def get_song_name(song_info: Dict[str, Any]) -> str:
    return song_info['item']['name']


def get_album_name(song_info: Dict[str, Any]) -> str:
    return song_info['item']['album']['name']


def get_song_duration(song_info: Dict[str, Any]) -> int:
    return song_info['item']['duration_ms']


def get_song_progress(song_info: Dict[str, Any]) -> int:
    return song_info['progress_ms']



def is_song_playing(song_info: Dict[str, Any]) -> bool:
    return song_info['is_playing']