import time
from urllib.parse import quote, urljoin
from playwright.sync_api import sync_playwright
from youtube_utils import get_duration_in_seconds, parse_year_from_text

def build_search_url(course_name: str) -> str:
    modified = f"{course_name} in English -Hindi -हिन्दी"
    return (
        "https://www.youtube.com/results"
        f"?search_query={quote(modified)}"
        "&sp=EgIQAw%253D%253D"
    )

def extract_playlist_view_count(playlist_page):
    view_spans = playlist_page.locator(
        "yt-content-metadata-view-model span.yt-core-attributed-string"
    )
    for i in range(view_spans.count()):
        text = view_spans.nth(i).text_content().strip()
        if "views" in text.lower():
            import re
            m = re.search(r"(\d[\d,]*)", text)
            if m:
                return int(m.group(1).replace(",", ""))
    return 0

def extract_first_video_year(playlist_page):
    stats = playlist_page.locator(
        "yt-formatted-string#video-info span.style-scope.yt-formatted-string"
    )
    texts = [stats.nth(i).text_content().strip() for i in range(stats.count())]
    return parse_year_from_text(texts)

def scrape_playlists(course_name: str, headless: bool = True) -> dict:
    search_url = build_search_url(course_name)
    base = "https://www.youtube.com"
    out = {"search_url": search_url, "playlists": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(search_url, timeout=120_000)
        page.wait_for_load_state("networkidle")
        
        #page_scroll
        for _ in range(20):
            page.keyboard.press("PageDown")
            time.sleep(0.3)

        cards = page.locator("yt-lockup-view-model.ytd-item-section-renderer.lockup")
        total = cards.count()
        print(f"▶️ Found {total} playlist cards")

        for i in range(total):
            card = cards.nth(i)
            tloc = card.locator("h3 a.yt-lockup-metadata-view-model-wiz__title")
            title = (tloc.get_attribute("title") or tloc.text_content() or "").strip()
            href = tloc.get_attribute("href") or ""
            url = urljoin(base, href)

            badge = card.locator("div.badge-shape-wiz__text").first
            raw = badge.text_content().strip() if badge.count() else ""
            import re
            m = re.search(r"(\d+)", raw.replace(",", ""))
            count = int(m.group(1)) if m else 0

            if count >= 20:
                continue

            view_link = card.locator("a.yt-core-attributed-string__link", has_text="View full playlist").first
            if not view_link.count():
                continue
            full_playlist_url = urljoin(base, view_link.get_attribute("href"))

            playlist_page = browser.new_page()
            playlist_page.goto(full_playlist_url, timeout=120_000)
            playlist_page.wait_for_timeout(3000)
            playlist_page.keyboard.press("PageDown")
            time.sleep(1)

            durations = playlist_page.locator(
                "div.thumbnail-overlay-badge-shape.style-scope.ytd-thumbnail-overlay-time-status-renderer >> div.badge-shape-wiz__text"
            )
            long_video_found = False

            for j in range(durations.count()):
                text = durations.nth(j).text_content().strip()
                if get_duration_in_seconds(text) > 1800:
                    long_video_found = True
                    break

            if not long_video_found:
                views = extract_playlist_view_count(playlist_page)
                year = extract_first_video_year(playlist_page)

                out["playlists"].append({
                    "title": title,
                    "url": url,
                    "video_count": count,
                    "full_playlist_url": full_playlist_url,
                    "views": views,
                    "year": year
                })

            playlist_page.close()

        browser.close()

    out["playlists"].sort(key=lambda x: (-x["views"], -x["year"]))
    return out