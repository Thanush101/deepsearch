# import gradio as gr
# import subprocess
# import json
# import os
# from typing import Tuple, Dict, List, Any

# # Install Playwright if not already installed
# try:
#     subprocess.run(["playwright", "install", "--with-deps", "chromium"], check=True)
#     print("✅ Playwright installed successfully")
# except Exception as e:
#     print(f"⚠️ Playwright installation error: {e}")

# # Import the necessary functions
# # Note: These imports assume that the modules are in the same directory
# try:
#     from scraper import scrape_playlists
#     from aws_llm import llm_response
#     print("✅ Custom modules imported successfully")
# except ImportError as e:
#     print(f"⚠️ Import error: {e}")
#     print("Please make sure 'scraper.py' and 'aws_llm.py' are in the same directory")

# def process_course(course_name: str, advanced_options: Dict[str, Any] = None) -> Tuple[str, str, str]:
#     """
#     Process the course by scraping playlists and selecting the best one.
    
#     Args:
#         course_name: The name of the course to search for
#         advanced_options: Dictionary of advanced options
        
#     Returns:
#         Tuple of (results_markdown, json_data, best_playlist)
#     """
#     try:
#         # Default options
#         options = {
#             "headless": True,
#             "max_duration": 30
#         }
        
#         # Update with any advanced options
#         if advanced_options:
#             options.update(advanced_options)
            
#         # Scrape the playlists
#         data = scrape_playlists(course_name, headless=True)
        
#         # Save the results to a JSON file
#         output_file = f"{course_name.replace(' ', '_')}_playlists.json"
#         with open(output_file, "w", encoding="utf-8") as f:
#             json.dump(data, f, indent=2, ensure_ascii=False)
        
#         # Prepare results markdown
#         results_md = f"## Search Results for: {course_name}\n\n"
#         results_md += f"Found {len(data['playlists'])} playlists with all videos <= {options['max_duration']} minutes:\n\n"
        
#         for pl in data["playlists"]:
#             results_md += f"### {pl['title']}\n"
#             results_md += f"- Videos: {pl['video_count']}\n"
#             results_md += f"- Views: {pl['views']}\n"
#             results_md += f"- Year: {pl['year']}\n"
#             results_md += f"- URL: [{pl['full_playlist_url']}]({pl['full_playlist_url']})\n\n"
        
#         # Format the playlist info for the LLM
#         playlist_infos = [
#             {
#                 "title": pl["title"],
#                 "url": pl["full_playlist_url"],
#                 "views": pl["views"],
#                 "year": pl["year"]
#             }
#             for pl in data["playlists"]
#         ]
        
#         # Get LLM recommendation
#         system_prompt = "You are an expert YouTube playlist selector."
#         user_prompt = (
#     f"Given the following YouTube playlists for '{course_name}', "
#     "select the single best playlist according to these criteria:\n"
#     "  1. Title and metadata indicate the content is in English.\n"
#     "  2. Total view count is as high as possible.\n"
#     "  3. Upload recency: prefer newer playlists, but allow ones up to 3 years old if they have significantly higher views.\n"
#     "  4. Exclude any playlist whose most recent video is older than 5 years.\n\n"
#     "Return your choice as a JSON object with the keys:\n"
#     "  {\n"
#     "    \"title\": <playlist title>,\n"
#     "    \"url\":   <playlist URL>,\n"
#     "    \"views\": <total view count>,\n"
#     "    \"year\":  <year of the most recent video>\n"
#     "  }\n\n"
#     "Here are the candidate playlists:\n"
#     f"{json.dumps(playlist_infos, indent=2)}"
# )




#         # user_prompt = (
#         #     f"Given the following YouTube playlists for {course_name}, "
#         #     "choose the best playlist that is in English, has the highest views, "
#         #     "and is the most recent. Only consider playlists where the title and metadata suggest the content is in English. "
#         #     "Return the best playlist as a JSON object with keys: title, url, views, year.\n\n"
#         #     f"Playlists:\n{json.dumps(playlist_infos, indent=2)}"
#         # )
        
#         best_playlist, cost = llm_response(system_prompt, user_prompt)

#         # Parse LLM response to dict for Gradio JSON component
#         try:
#             best_playlist_json = json.loads(best_playlist)
#         except Exception:
#             best_playlist_json = {"error": "LLM did not return valid JSON", "raw": best_playlist}

#         # Add LLM recommendation to markdown
#         results_md += f"## AI Recommendation\n\n"
#         results_md += f"Best English Playlist (selected by AI):\n\n"
#         results_md += f"```json\n{best_playlist}\n```\n\n"
#         results_md += f"Estimated LLM cost: ${cost:.6f}"

#         return results_md, json.dumps(data, indent=2), best_playlist_json
    
#     except Exception as e:
#         error_message = f"## Error\n\nAn error occurred: {str(e)}"
#         return error_message, {}, {}

# def create_interface():
#     """Create and launch the Gradio interface."""
    
#     with gr.Blocks(title="YouTube Course Playlist Finder", theme=gr.themes.Soft()) as app:
#         gr.Markdown("# YouTube Course Playlist Finder")
#         gr.Markdown("Search for educational playlists on YouTube and get AI recommendations for the best one.")
        
#         with gr.Row():
#             with gr.Column(scale=2):
#                 course_input = gr.Textbox(
#                     label="Course Name",
#                     placeholder="Enter a course name (e.g., 'python programming', 'machine learning basics')",
#                     value="python programming"
#                 )
#                 search_btn = gr.Button("Search", variant="primary")
                
#             with gr.Column(scale=1):
#                 with gr.Accordion("Advanced Options", open=False):
#                     headless_checkbox = gr.Checkbox(
#                         label="Run Browser in Headless Mode",
#                         value=True
#                     )
#                     max_duration = gr.Slider(
#                         minimum=5,
#                         maximum=60,
#                         step=5,
#                         value=30,
#                         label="Maximum Video Duration (minutes)"
#                     )
        
#         with gr.Tabs():
#             with gr.TabItem("Results"):
#                 results_md = gr.Markdown()
            
#             with gr.TabItem("Raw JSON Data"):
#                 json_output = gr.JSON()
            
#             with gr.TabItem("Best Playlist"):
#                 best_playlist_json = gr.JSON()
        
#         search_btn.click(
#             fn=process_course,
#             inputs=[
#                 course_input,
#                 gr.Json({
#                     "headless": headless_checkbox,
#                     "max_duration": max_duration
#                 })
#             ],
#             outputs=[results_md, json_output, best_playlist_json]
#         )
        
#         # Add example inputs
#         gr.Examples(
#             examples=[
#                 ["python programming"],
#                 ["machine learning for beginners"],
#                 ["javascript tutorial"],
#                 ["react js tutorial"],
#                 ["data science with python"]
#             ],
#             inputs=course_input
#         )
    
#     return app

# if __name__ == "__main__":
#     # Create and launch the Gradio app
#     app = create_interface()
#     app.launch(share=True)





# import os
# import sys
# import gradio as gr
# import subprocess
# import json
# import os
# import re
# from typing import Tuple, Dict, Any
# from playlist_details import get_youtube_playlist_videos

# # Ensure Playwright & browsers are installed
# try:
#     subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
#     print("Playwright browsers installed")
# except Exception as e:
#     print(f"Playwright install failed: {e}")
# # Import custom modules (ensure they are in the working directory)
# from scraper import scrape_playlists
# from aws_llm import llm_response

# def process_course(course_name: str, advanced_options: Dict[str, Any] = None) -> dict:
#     try:
#         data = scrape_playlists(course_name, headless=True)
#         playlist_infos = [
#             {
#                 "title": pl["title"],
#                 "url": pl["full_playlist_url"],
#                 "views": pl["views"],
#                 "year": pl["year"]
#             }
#             for pl in data["playlists"]
#         ]
#         system_prompt = "You are an expert YouTube playlist selector."
#         user_prompt = (
#             f"Given the following YouTube playlists for {course_name}, "
#             "choose the best playlist that is in English, has the highest views, "
#             "and is the most recent. Only consider playlists where the title and metadata suggest the content is in English. "
#             "Return the best playlist as a JSON object with keys: title, url.\n\n"
#             f"Playlists:\n{json.dumps(playlist_infos, indent=2)}"
#         )
#         best_playlist, _ = llm_response(system_prompt, user_prompt)
#         # Extract playlist URL from LLM response
#         match = re.search(r'\{[^{}]*"title"[^{}]*"url"[^{}]*\}', best_playlist, re.DOTALL)
#         if match:
#             playlist_json = json.loads(match.group(0))
#             playlist_url = playlist_json.get("url", "")
#             if playlist_url:
#                 # Call your detailed playlist function
#                 result = get_youtube_playlist_videos(playlist_url)
#                 return result
#         return {"error": "Could not extract playlist URL"}
#     except Exception as e:
#         return {"error": str(e)}

# def create_interface():
#     with gr.Blocks(theme=gr.themes.Soft(), css=".gradio-container {max-width: 800px; margin: auto;} .output-markdown {white-space: pre-wrap;}") as app:
#         gr.Markdown("# YouTube Course Playlist Finder")
#         gr.Markdown("Search YouTube playlists Agent")

#         course = gr.Textbox(label="Course Name", placeholder="e.g., Python programming", value="Python programming")
#         search = gr.Button("Search", variant="primary")

#         with gr.Tabs():
#             with gr.TabItem("Best Playlist"):
#                 best_json = gr.JSON(label="AI Selected Playlist")    

#         search.click(fn=process_course, inputs=[course], outputs=[best_json])

#         gr.Examples(examples=["python programming", "machine learning", "react js tutorial"], inputs=course)

#     return app

# if __name__ == "__main__":
#     app = create_interface()
#     app.launch(server_name="0.0.0.0", server_port=8080,share=True)



import os

# Ensure Playwright and its dependencies are installed on Streamlit Cloud
os.system("playwright install chromium")
os.system("playwright install-deps")

import sys
from datetime import datetime
import streamlit as st
import json

# --- Windows asyncio event loop fix for Playwright ---
if sys.platform.startswith("win"):
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Custom modules
from playwright.sync_api import sync_playwright
from aws_llm import llm_response
from playlist_details import get_youtube_playlist_videos
from scraper import scrape_playlists

# Streamlit App Configuration
st.set_page_config(page_title="YouTube Course Playlist Finder", layout="centered")
st.title("YouTube Course Playlist Finder")
st.markdown("Search YouTube playlists using an AI-powered agent.")

@st.cache_data
def process_course(course_name: str) -> dict:
    try:
        # Scrape playlists matching the course name
        data = scrape_playlists(course_name, headless=True)
        playlist_infos = [
            {
                "title": pl["title"],
                "url": pl["full_playlist_url"],
                "views": pl["views"],
                "year": pl["year"]
            }
            for pl in data.get("playlists", [])
        ]

        # Compose prompts for the LLM
        system_prompt = "You are an expert YouTube playlist selector."
        user_prompt = (
            f"Given the following YouTube playlists for {course_name}, "
            "choose the best playlist that is in English, has the highest views, "
            "and is the most recent. Only consider playlists where the title and metadata suggest the content is in English. "
            "Return the best playlist as a JSON object with keys: title, url.\n\n"
            f"Playlists:\n{json.dumps(playlist_infos, indent=2)}"
        )
        best_playlist, _ = llm_response(system_prompt, user_prompt)

        # Extract playlist URL from LLM response
        import re
        match = re.search(r'\{[^{}]*"title"[^{}]*"url"[^{}]*\}', best_playlist, re.DOTALL)
        if match:
            playlist_json = json.loads(match.group(0))
            playlist_url = playlist_json.get("url", "")
            if playlist_url:
                # Fetch detailed video information
                return get_youtube_playlist_videos(playlist_url)
        return {"error": "Could not extract playlist URL from LLM response."}

    except Exception as e:
        return {"error": str(e)}

# User input
course_name = st.text_input("Course Name", value="Python programming", placeholder="e.g., Python programming")
search_button = st.button("Search")

# Display results when clicked
if search_button:
    with st.spinner("Finding the best playlist..."):
        result = process_course(course_name)
    if "error" in result:
        st.error(result["error"])
    else:
        tabs = st.tabs(["Best Playlist Details"])
        with tabs[0]:
            st.json(result)

# Example inputs
st.markdown("---")
st.markdown("**Examples:**")
st.write("- python programming")
st.write("- machine learning")
st.write("- react js tutorial")