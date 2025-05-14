from aws_llm import llm_response
import json
from .prompts import MCQ_SYSTEM_PROMPT , MCQ_USER_PROMPT , LEARN_SYSTEM_PROMPT,LEARN_USER_PROMPT,PLAYLIST_MCQ_SYSTEM_PROMPT,PLAYLIST_MCQ_USER_PROMPT

def generate_mcqs(material, num_questions=5):
    """Generate MCQs using the LLM."""
    try:
        user_prompt = MCQ_USER_PROMPT.format(material=material, num_questions=num_questions)
        system_prompt = MCQ_SYSTEM_PROMPT.format(num_questions=num_questions)
        response, cost = llm_response(system_prompt, user_prompt)
        
        # Parse JSON response
        questions = json.loads(response)
        return questions, cost
    except Exception as e:
        print(f"⚠️ Error generating MCQs: {e}")
        # Return a fallback question if generation fails
        return [
            {
                "question": "What is the main topic of this content?",
                "options": [
                    "Unable to determine",
                    "Content unavailable",
                    "Error in processing",
                    "Question generation failed"
                ],
                "answer": "Error in processing"
            }
        ], 0



def generate_learning_outcomes(material):
    """Generate 'What You'll Learn' points using the LLM."""
    try:
        user_prompt = LEARN_USER_PROMPT.format(material=material)
        response, cost = llm_response(LEARN_SYSTEM_PROMPT, user_prompt)
        
        # Parse JSON response
        learning_outcomes = json.loads(response)
        return learning_outcomes, cost
    except Exception as e:
        print(f"⚠️ Error generating learning outcomes: {e}")
        return ["Understand key concepts covered in this content"], 0
    


    
def generate_playlist_mcqs(playlist_title, video_summaries, num_questions=10):
    """Generate overall playlist MCQs using the LLM."""
    try:
        # Create a condensed summary of all videos for context
        summaries_text = "\n\n".join([f"Video: {summary['title']}\nSummary: {summary['description']}" 
                                     for summary in video_summaries[:20]])  # Limit to avoid token limits
        
        user_prompt = PLAYLIST_MCQ_USER_PROMPT.format(
            playlist_title=playlist_title,
            video_summaries=summaries_text,
            num_questions=num_questions
        )
        system_prompt = PLAYLIST_MCQ_SYSTEM_PROMPT.format(num_questions=num_questions)
        response, cost = llm_response(system_prompt, user_prompt)
        
        # Parse JSON response
        questions = json.loads(response)
        return questions, cost
    except Exception as e:
        print(f"⚠️ Error generating playlist MCQs: {e}")
        # Return a fallback question if generation fails
        return [
            {
                "question": "What is the main theme of this playlist?",
                "options": [
                    "Unable to determine",
                    "Content unavailable",
                    "Error in processing",
                    "Question generation failed"
                ],
                "answer": "Error in processing"
            }
        ], 0
