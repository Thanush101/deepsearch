import os
import re
import time
import json
import urllib.parse
import concurrent.futures
from urllib.parse import urlparse, parse_qs
from utils.prompts import DESCRIPTION_SYSTEM_PROMPT,DESCRIPTION_USER_PROMPT
from aws_llm import llm_response
from utils.transcript import fetch_transcript

def get_thumbnail_url(video_href: str) -> str:
    parsed = urllib.parse.urlparse(video_href)
    query = urllib.parse.parse_qs(parsed.query)
    video_id = query.get("v", [None])[0]
    if video_id:
        return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    return None

def parse_video_id(url: str) -> str:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "v" not in qs or not qs["v"]:
        raise ValueError(f"No video ID in URL: {url}")
    return qs["v"][0]


def duration_in_range(raw_duration: str, min_min: int = 2, max_min: int = 80) -> bool:
    try:
        parts = [int(p) for p in raw_duration.split(":")]
        if len(parts) == 3:
            hrs, mins, secs = parts
            total = hrs * 60 + mins + secs / 60
        elif len(parts) == 2:
            mins, secs = parts
            total = mins + secs / 60
        else:
            return False
        return min_min <= total <= max_min
    except ValueError:
        return False
    
def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()


def process_video_data(vid_data):
    try:
        vid_id = vid_data["video_id"]
        title = vid_data["title"]
        transcript = ""
        try:
            transcript = fetch_transcript(vid_id)
        except Exception as e:
            print(f"⚠️ Transcript failed for {title}: {e}")
        material = transcript.strip() or title
        user_prompt = DESCRIPTION_USER_PROMPT.format(material=material)
        description, cost = llm_response(DESCRIPTION_SYSTEM_PROMPT, user_prompt)
        return {**vid_data, "transcript": transcript, "description": description, "llm_cost": cost}
    except Exception as e:
        print(f"Error processing video {vid_data.get('title', 'unknown')}: {e}")
        return vid_data