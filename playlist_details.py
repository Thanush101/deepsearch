import os
import re
import time
import json
import urllib.parse
import concurrent.futures
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
from aws_llm import llm_response
from utils.generator import generate_learning_outcomes,generate_mcqs,generate_playlist_mcqs
from utils.transcript import fetch_transcript
from helper.helpers import get_thumbnail_url,parse_video_id,sanitize_filename,duration_in_range

# Prompts for description generation
DESCRIPTION_SYSTEM_PROMPT = (
    "You are a professional writing assistant.\n"
    "Your task is to transform the following YouTube video description into a clean, concise, and informative summary.About the Course section—similar to what you'd find on a professional course page.\n"
    "Present the content as clear, well-written bullet points, each conveying one key idea.\n"
    "Eliminate timestamps, repetitive phrases, promotional content, and irrelevant information.\n"
    "Ensure the language is natural, professional, and sounds like it was written by a human expert.\n"
    "If only the title is available, infer the likely content and generate a meaningful, accurate summary based on it.\n"
    "**IMPORTANT** Do not include any introductions, explanations, or labels such as 'Summary' or 'Cleaned Description.'"
    "Always provide the best possible output using your reasoning and language skills, regardless of the input quality."
)

DESCRIPTION_USER_PROMPT = (
    "Material:\n{material}"
)

def get_youtube_playlist_videos(url: str, mcq_per_video=5, playlist_mcqs=10):
    output = {
        "playlist_info": {
            "title": "", 
            "channel": "", 
            "url": url, 
            "channel_icon": "",
            "what_you_learn": []
        },
        "videos": [],
        "playlist_questions": []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = context.new_page()
        page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2}", 
                   lambda route: route.abort() if "i.ytimg.com/vi" not in route.request.url else route.continue_())
        page.goto(url, wait_until="networkidle", timeout=30000)

        # Extract playlist title
        try:
            # Try the most common selector
            playlist_title = page.evaluate(
                "() => document.querySelector('h1#title yt-formatted-string')?.textContent?.trim()"
            )
            if not playlist_title:
                # Try YouTube's new layout selector
                playlist_title = page.evaluate(
                    "() => document.querySelector('yt-dynamic-sizing-formatted-string#title')?.textContent?.trim()"
                )
            if not playlist_title:
                # Try fallback: meta og:title
                playlist_title = page.evaluate(
                    "() => document.querySelector('meta[property=\\'og:title\\']')?.content?.trim()"
                )
            if not playlist_title:
                # Try span with yt-core-attributed-string class (new YouTube layout)
                playlist_title = page.evaluate(
                    "() => {\n  const el = document.querySelector('span.yt-core-attributed-string.yt-core-attributed-string--white-space-pre-wrap[role=text]');\n  return el ? el.textContent.trim() : null;\n}"
                )
            if not playlist_title:
                # Try fallback: <title> tag
                playlist_title = page.title()
                # Remove trailing ' - YouTube' if present
                if playlist_title and playlist_title.endswith(' - YouTube'):
                    playlist_title = playlist_title.replace(' - YouTube', '').strip()
            if playlist_title:
                output["playlist_info"]["title"] = playlist_title
            else:
                # Fallback: Try BeautifulSoup if Playwright fails
                soup_title = BeautifulSoup(page.content(), "html.parser")
                title_el = soup_title.select_one("h1#title yt-formatted-string")
                if not title_el:
                    title_el = soup_title.select_one("yt-dynamic-sizing-formatted-string#title")
                if not title_el:
                    meta_og = soup_title.find("meta", {"property": "og:title"})
                    if meta_og:
                        playlist_title = meta_og.get("content", "").strip()
                        output["playlist_info"]["title"] = playlist_title
                elif title_el:
                    output["playlist_info"]["title"] = title_el.text.strip()
        except Exception as e:
            print(f"⚠️ Could not extract playlist title: {e}")

        # Get total video count
        try:
            page.wait_for_selector(".metadata-stats.style-scope.ytd-playlist-byline-renderer", timeout=10000)
            video_count_text = page.evaluate(
                "() => document.querySelector('.metadata-stats.style-scope.ytd-playlist-byline-renderer yt-formatted-string.byline-item span')?.textContent.trim() || '0'"
            )
            total_videos = int(video_count_text) if video_count_text.isdigit() else 0
            output["playlist_info"]["video_count"] = total_videos
            print(f"📋 Playlist contains {total_videos} videos according to YouTube")

            # Improved dynamic scrolling
            max_attempts = min((total_videos // 5) + 50, 200)  # Cap max attempts for very large playlists
            attempt = 0
            prev_loaded = 0
            no_change_count = 0
            print(f"🖱️ Scrolling dynamically to load all videos...")
            
            while True:
                attempt += 1
                
                # Scroll to the bottom more precisely using JavaScript
                page.evaluate("""
                    () => {
                        const container = document.querySelector('ytd-playlist-video-list-renderer');
                        if (container) {
                            container.scrollTop = container.scrollHeight;
                            window.scrollTo(0, document.body.scrollHeight);
                        } else {
                            window.scrollTo(0, document.body.scrollHeight);
                        }
                    }
                """)
                
                # Wait for network to be idle (more robust than fixed time)
                page.wait_for_timeout(1000)  # Initial wait for scroll action
                try:
                    page.wait_for_load_state("networkidle", timeout=3000)  # Wait for network activity to settle
                except:
                    pass  # Continue if timeout occurs
                
                # Count loaded videos
                loaded_count = page.evaluate(
                    "() => document.querySelectorAll('ytd-playlist-video-renderer').length"
                )
                
                print(f"  ↳ Attempt {attempt}: loaded {loaded_count}/{total_videos}")
                
                # Check for completion or stalled loading
                if loaded_count >= total_videos:
                    print("✅ All videos loaded!")
                    break
                    
                if loaded_count == prev_loaded:
                    no_change_count += 1
                    if no_change_count >= 5:  # If no new videos loaded after 5 attempts
                        print(f"⚠️ Scrolling stalled at {loaded_count}/{total_videos} videos")
                        
                        # Try one more aggressive scroll technique
                        try:
                            print("Attempting more aggressive scrolling technique...")
                            # Click on the last visible video to ensure it's in view
                            page.evaluate("""
                                () => {
                                    const videos = document.querySelectorAll('ytd-playlist-video-renderer');
                                    if (videos.length > 0) {
                                        const lastVideo = videos[videos.length - 1];
                                        lastVideo.scrollIntoView({behavior: 'smooth', block: 'end'});
                                    }
                                }
                            """)
                            page.wait_for_timeout(2000)
                            
                            # Force scroll beyond the current view
                            page.evaluate("""
                                () => {
                                    window.scrollBy(0, window.innerHeight * 2);
                                }
                            """)
                            page.wait_for_timeout(2000)
                            
                            # Check if this helped
                            new_count = page.evaluate(
                                "() => document.querySelectorAll('ytd-playlist-video-renderer').length"
                            )
                            
                            if new_count > loaded_count:
                                print(f"  ↳ Aggressive scroll worked! Now at {new_count} videos")
                                no_change_count = 0
                                prev_loaded = new_count
                                continue
                        except:
                            pass
                            
                        print(f"⚠️ Giving up after {attempt} attempts; proceeding with {loaded_count} videos")
                        break
                else:
                    no_change_count = 0
                    prev_loaded = loaded_count
                    
                if attempt >= max_attempts:
                    print(f"⚠️ Max scroll attempts reached ({max_attempts}); proceeding with {loaded_count} videos")
                    break
                    
        except Exception as e:
            print(f"⚠️ Error during scrolling: {e}")

        # Final content load and parse
        # Ensure we're at the very bottom one last time
        page.evaluate("""
            () => {
                window.scrollTo(0, document.body.scrollHeight * 2);
                const container = document.querySelector('ytd-playlist-video-list-renderer');
                if (container) container.scrollTop = container.scrollHeight * 2;
            }
        """)
        page.wait_for_timeout(2000)  # Give time for final items to load
        
        loaded_video_count = page.evaluate(
            "() => document.querySelectorAll('ytd-playlist-video-renderer').length"
        )
        print(f"🔢 Actually loaded {loaded_video_count} videos")

        soup = BeautifulSoup(page.content(), "html.parser")
        video_elements = soup.select("ytd-playlist-video-renderer")
        if c := soup.select_one("ytd-channel-name div#text-container a"): output["playlist_info"]["channel"] = c.text.strip()

        # Robust channel_icon extraction with debug output
        # 1. Try playlist header avatar (most reliable)
        header_avatar = soup.select_one("img.yt-core-image.yt-spec-avatar-shape__image")
        if header_avatar and header_avatar.get("src"):
            output["playlist_info"]["channel_icon"] = header_avatar["src"]
            print("[DEBUG] channel_icon found from playlist header avatar selector (.yt-core-image.yt-spec-avatar-shape__image)")
        else:
            found = False
            # 2. Try first video's channel avatar
            if video_elements:
                a = video_elements[0].select_one("a#video-title")
                if a:
                    first_video_url = "https://www.youtube.com" + a["href"]
                    try:
                        icon_page = context.new_page()
                        icon_page.goto(first_video_url, wait_until="domcontentloaded", timeout=30000)
                        icon_page.wait_for_selector("yt-img-shadow#avatar img#img", timeout=10000)
                        icon_el = icon_page.query_selector("yt-img-shadow#avatar img#img")
                        if icon_el:
                            icon_src = icon_el.get_attribute("src")
                            if icon_src:
                                output["playlist_info"]["channel_icon"] = icon_src
                                found = True
                                print("[DEBUG] channel_icon found from first video owner selector (yt-img-shadow#avatar img#img)")
                        icon_page.close()
                    except Exception as e:
                        print(f"[DEBUG] channel_icon NOT found in first video owner selector: {e}")
            if not found:
                # 3. Fallback to default icon
                output["playlist_info"]["channel_icon"] = "https://www.youtube.com/img/desktop/yt_1200.png"
                print("[DEBUG] channel_icon fallback to default icon")

        # For collecting video summaries for later playlist-level MCQ generation
        all_video_summaries = []
        all_transcripts = []

        # Process videos
        print(f"🔍 Found {len(video_elements)} videos to process")
        for idx, vid in enumerate(video_elements):
            a = vid.select_one("a#video-title")
            if not a: continue
            title = a["title"].strip()
            href = a["href"]
            full_url = "https://www.youtube.com" + href
            thumb = get_thumbnail_url(href)
            raw_dur = vid.select_one("badge-shape .badge-shape-wiz__text").text.strip() if vid.select_one("badge-shape .badge-shape-wiz__text") else "0:00"
            if not duration_in_range(raw_dur):
                print(f"⏭️ Skipping '{title}'—duration {raw_dur}")
                continue
            vid_id = parse_video_id(full_url)
            transcript = ""
            try:
                transcript = fetch_transcript(vid_id)
            except Exception as e:
                print(f"⚠️ Transcript failed for {title}: {e}")
            
            material = transcript.strip() or title
            all_transcripts.append(material)
            
            # Generate video description
            user_prompt = DESCRIPTION_USER_PROMPT.format(material=material)
            description, cost = llm_response(DESCRIPTION_SYSTEM_PROMPT, user_prompt)
            
            # Generate MCQs for this video
            print(f"🧩 Generating {mcq_per_video} MCQs for video: {title}")
            mcqs, mcq_cost = generate_mcqs(material, mcq_per_video)
            
            # Generate "What You'll Learn" points for this video
            print(f"📝 Generating learning outcomes for video: {title}")
            learning_outcomes, learn_cost = generate_learning_outcomes(material)
            
            # Store video summary for playlist-level MCQs
            all_video_summaries.append({
                "title": title,
                "description": description
            })
            
            if idx == 0 and not output["playlist_info"]["channel_icon"]:
                try:
                    icon_page = context.new_page()
                    icon_page.goto(full_url, wait_until="domcontentloaded", timeout=15000)
                    icon_page.wait_for_selector("ytd-video-owner-renderer img#img", timeout=5000)
                    icon_el = icon_page.query_selector("ytd-video-owner-renderer img#img")
                    output["playlist_info"]["channel_icon"] = icon_el.get_attribute("src")
                    icon_page.close()
                except:
                    pass
                    
            output["videos"].append({
                "title": title,
                "url": full_url,
                "thumbnail": thumb,
                "duration": raw_dur,
                "description": description,
                "questions": mcqs,
                "what_you_learn": learning_outcomes
            })
            
            if (idx + 1) % 10 == 0 or idx == 0 or idx == len(video_elements) - 1:
                print(f"⏱️ Processed {idx+1}/{len(video_elements)} videos ({((idx+1)/len(video_elements)*100):.1f}%)")

        # After processing all videos, generate playlist-level content
        print(f"🧩 Generating {playlist_mcqs} MCQs for the entire playlist")
        playlist_title = output["playlist_info"]["title"]
        
        # Generate playlist-level MCQs
        playlist_mcqs_result, playlist_mcq_cost = generate_playlist_mcqs(
            playlist_title, 
            all_video_summaries,
            playlist_mcqs
        )
        output["playlist_questions"] = playlist_mcqs_result
        
        # Generate overall learning outcomes for the playlist
        combined_material = "\n\n".join([
            f"Title: {output['playlist_info']['title']}",
            *[summary["description"] for summary in all_video_summaries[:10]]  # Use first 10 videos to avoid token limits
        ])
        playlist_outcomes, playlist_learn_cost = generate_learning_outcomes(combined_material)
        output["playlist_info"]["what_you_learn"] = playlist_outcomes
        
        context.close()
        browser.close()

    # Ensure channel_icon is never empty
    if not output["playlist_info"].get("channel_icon"):
        output["playlist_info"]["channel_icon"] = "https://www.youtube.com/img/desktop/yt_1200.png"
    return output

if __name__ == "__main__":
    start_time = time.time()
    os.environ["PYTHONUNBUFFERED"] = "1"
    PLAYLIST_URL = os.getenv("PLAYLIST_URL", "https://www.youtube.com/playlist?list=PLeo1K3hjS3uuKaU2nBDwr6zrSOTzNCs0l")
    
    # MCQ generation parameters - can be configured via environment variables
    MCQ_PER_VIDEO = int(os.getenv("MCQ_PER_VIDEO", "5"))
    PLAYLIST_MCQS = int(os.getenv("PLAYLIST_MCQS", "10"))
    
    print(f"🔍 Scraping playlist: {PLAYLIST_URL}")
    print(f"🧩 Will generate {MCQ_PER_VIDEO} MCQs per video and {PLAYLIST_MCQS} for the playlist")
    
    data = get_youtube_playlist_videos(
        PLAYLIST_URL,
        mcq_per_video=MCQ_PER_VIDEO,
        playlist_mcqs=PLAYLIST_MCQS
    )
    
    title = data["playlist_info"]["title"] or "playlist"
    filename = sanitize_filename(title) + ".json"
    os.makedirs("outputs", exist_ok=True)
    filepath = os.path.join("outputs", filename)
    
    elapsed = time.time() - start_time
    print(f"✅ Completed in {elapsed:.2f} seconds")
    print(f"📄 Saved {len(data['videos'])} videos (with descriptions, MCQs, and learning outcomes) to {filepath}")
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)