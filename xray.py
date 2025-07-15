import json
import logging
from typing import Any, Dict, List

import redis
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from vertexai.generative_models import Tool, grounding

from utils import get_artists, get_song_id, get_song_name

# Load environment variables from a .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Define the desired JSON schema for the song information.
class SongInfo(BaseModel):
    meaning: str = Field(
        description="The deep meaning and artist's intent behind the song."
    )
    facts: List[str] = Field(
        description="A list of interesting facts and anecdotes about the song."
    )


google_search_tool = Tool.from_google_search_retrieval(
    grounding.GoogleSearchRetrieval()
)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.01,
    model_kwargs={"tools": [google_search_tool]},
).with_structured_output(SongInfo)


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a highly knowledgeable music analysis AI. Your goal is to provide "
            "factually accurate information about songs by leveraging Google Search. "
            "Make sure to *ALWAYS* fetch latest information from the web before performing any analysis. "
            "For each song, provide its deep meaning and artist's interpretation of the song. "
            "Also provide a list of interesting facts / tidbits which maybe be lesser know or unknown to the world. "
            "If you can't find any information, return an empty string for 'meaning' and an empty list for 'facts'.",
        ),
        ("human", "Song Name: {song_name}\nArtist(s): {artist_name}"),
    ]
)

chain = prompt | llm


def get_song_info(
    redis_client: redis.Redis, song_info: Dict[str, Any]
) -> Dict[str, str | List[str]]:
    # logger.info(f"Initializing analysis for '{song_name}' by {artist_name}")
    # Check if the song info is already cached in Redis
    song_name = get_song_name(song_info)
    artist_name_str, _ = get_artists(song_info)
    song_id = get_song_id(song_info)

    cache_key = f"song_info:{song_id}"
    cached_info = redis_client.get(cache_key)

    if cached_info:
        logger.info(f"Cache hit for: {song_name} by {artist_name_str}")
        return json.loads(str(cached_info))

    logger.info(f"Cache miss for: {song_name} by {artist_name_str}")

    # If not cached, invoke the chain to get the song information
    logger.info(f"Searching for: {song_name} by {artist_name_str}")
    response = chain.invoke({"song_name": song_name, "artist_name": artist_name_str})
    song_xray = {"meaning": response.meaning, "facts": response.facts}

    # Log the response, and store the result in cache
    logger.info(f"Analysis completed for: {song_name} by {artist_name_str}")
    redis_client.set(cache_key, json.dumps(song_xray), ex=86400)
    return song_xray


if __name__ == "__main__":
    try:
        song_name_1 = "Bloodstream"
        artist_name_1 = "The Chainsmokers"
        response_1 = get_song_info(song_name_1, artist_name_1)

        print(f"\n--- Results for '{song_name_1}' ---")
        print(f"Meaning: {response_1.meaning}")
        print("Facts:")
        for fact in response_1.facts:
            print(f"- {fact}")

    except Exception as e:
        logger.error(f"An error occurred during execution: {e}", exc_info=True)
        print(f"\nAn error occurred: {e}")
