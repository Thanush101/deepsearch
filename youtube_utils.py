import re
from datetime import datetime

def get_duration_in_seconds(text: str) -> int:
    parts = list(map(int, text.strip().split(":")))
    if len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds
    elif len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds
    return 0

def parse_year_from_text(texts):
    now = datetime.now().year
    for text in texts:
        if "year" in text:
            m = re.search(r"(\d+)", text)
            if m:
                return now - int(m.group(1))
        elif "month" in text:
            return now
    return 0