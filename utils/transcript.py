import os
import time
import requests
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

# Define a proxies dictionary for requests only
proxies = {
    "http": "http://Vv8lHp2g:kMhGaCi9XZ@103.172.84.179:50100",
    "https": "http://Vv8lHp2g:kMhGaCi9XZ@103.172.84.179:50100",
}

YTI_API_URL = "https://www.youtube-transcript.io/api/transcripts"
YTI_API_TOKENS = [
    "681c60baa1baf5a82dd5f382",
    "681c624386b69cddd17685ed",
    "681c628dde80881429decd76",
    "681c62bfa1baf5a82dd5f3b3",
    "681c62eade80881429decd7f",
    "68244ac37994b78ec23e3089",
    "68244c15f0a725b52f52477e",
    "68244c6d7994b78ec23e30b4",
]

def fetch_transcript(video_id: str, max_retries: int = 2, backoff_factor: float = 2.0) -> str:
    """
    Fetch YouTube transcript with three-tier fallback:
      1) YouTubeTranscriptApi (en, hi)
      2) youtube-transcript.io API (English)
      3) YouTube timedtext web endpoint (English)
    Retries each method up to max_retries with exponential backoff.
    Returns the full transcript as a single string.
    Raises the last exception if all methods fail.
    """
    def _retry(fn, *args, **kwargs):
        """Helper to retry a fetch function with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as err:
                if attempt < max_retries - 1:
                    wait = backoff_factor ** attempt
                    print(f"[Retry] {fn.__name__} failed (attempt {attempt+1}), retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    # Last attempt: re-raise
                    raise
    # --- Method 1: youtube_transcript_api ---
    def _yt_api():
        try:
            # Try direct get_transcript
            segs = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'hi'])
        except (TranscriptsDisabled, NoTranscriptFound):
            # Fallback to listing then manual/generate selection
            transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
            try:
                t = transcripts.find_transcript(['en'])
            except NoTranscriptFound:
                t = transcripts.find_generated_transcript(['hi'])
            segs = t.fetch()
        return " ".join(s['text'] for s in segs)

    try:
        return _retry(_yt_api)
    except Exception as e1:
        print(f"[Fallback 1 failed] {e1}")

    # --- Method 2: youtube-transcript.io API ---
    def _yti_api():
        last_err = None
        for token in YTI_API_TOKENS:
            try:
                resp = requests.post(
                    YTI_API_URL,
                    headers={
                        "Authorization": f"Basic {token}",
                        "Content-Type": "application/json"
                    },
                    json={"ids": [video_id]},
                    proxies=proxies
                )
                resp.raise_for_status()
                data = resp.json()
                segments = data.get(video_id, {}).get("segments", [])
                if not segments:
                    raise ValueError("No segments returned by youtube-transcript.io")
                return " ".join(seg["text"] for seg in segments)
            except Exception as e:
                last_err = e
                continue
        raise last_err

    try:
        return _retry(_yti_api)
    except Exception as e2:
        print(f"[Fallback 2 failed] {e2}")

    # --- Method 3: YouTube timedtext endpoint ---
    def _yt_timedtext():
        # construct the "web" captions endpoint
        url = (
            f"https://video.google.com/timedtext?"
            f"lang=en&v={video_id}"
        )
        resp = requests.get(url, timeout=10, proxies=proxies)
        resp.raise_for_status()
        # XML format: <transcript><text start="..." dur="...">...text...</text>...</transcript>
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.text)
        if not list(root):
            raise ValueError("No captions in timedtext response")
        # combine all text nodes
        return " ".join(node.text.strip().replace('\n', ' ') for node in root.findall('text') if node.text)

    # final attempt; if this fails it'll raise
    return _retry(_yt_timedtext)


