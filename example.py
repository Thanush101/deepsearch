import requests

def get_youtube_transcript(video_id, api_key, lang="en"):
    url = (
        "https://api.supadata.ai/v1/youtube/transcript/translation"
        f"?videoId={video_id}&lang={lang}&text=true"
    )
    headers = {
        "x-api-key": api_key
    }

    try:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()

        # Check for expected content
        if "content" in data and data["content"]:
            return data["content"]
        else:
            print("No transcript found or unsupported video.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")
        return None

# Your API key
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiIsImtpZCI6IjEifQ.eyJpc3MiOiJuYWRsZXMiLCJpYXQiOiIxNzQ3MjEzMzM0IiwicHVycG9zZSI6ImFwaV9hdXRoZW50aWNhdGlvbiIsInN1YiI6IjAzZjBiODYwNDYyOTRkNGRhZDYwZjVjYjllY2UwODdmIn0.hpCh68cYWlLoc3xcCPCp3DTxuNvMNYkOktNv-LxZf5o"

video_id = input("Enter YouTube video ID: ")
transcript = get_youtube_transcript(video_id, API_KEY)

if transcript:
    print("\nTranscript:")
    print(transcript)
else:
    print("Failed to retrieve transcript or transcript not available.")
