import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage


def generate_context_briefing(text_map, user_additional_context):  # <-- Modified
    """
    Generates a context briefing using AI summary and user-provided instructions.

    Args:
        text_map (list): The list of extracted text elements from Phase 1.
        user_additional_context (str): Specific instructions from the user via the GUI.
    """
    print("\n--- Starting Phase 2: Context Generation ---")

    if 'GOOGLE_API_KEY' not in os.environ:
        print("\nFATAL ERROR: GOOGLE_API_KEY environment variable not found.")
        return None

    all_text = " ".join([item['original_text'] for item in text_map])
    if not all_text.strip():
        print("No text found to generate a summary.")
        return "No text content found."

    print("Connecting to Google GenAI to generate a summary...")
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro-preview-06-05")
        summarizer_prompt = f"""
        You are a brilliant marketing strategist. Read the following presentation text dump and generate a concise summary (in English) to brief a translator.
        Focus on: Core Business Goal, Target Audience, Overall Tone, and Key Jargon.
        Here is the text:
        ---
        {all_text}
        ---
        """
        ai_response = llm.invoke([HumanMessage(content=summarizer_prompt)])
        ai_summary = ai_response.content
        print("\n--- AI-Generated Context Summary ---")
        print(ai_summary)
    except Exception as e:
        print(f"\nAn error occurred while communicating with the AI: {e}")
        return None

    # NO MORE input() call here. We use the argument directly.
    final_briefing = f"""--- CONTEXT BRIEFING FOR TRANSLATOR ---
**Part 1: AI-Generated Analysis**
{ai_summary}
**Part 2: Specific Instructions from User**
{user_additional_context if user_additional_context.strip() else "None."}
--- END OF BRIEFING ---"""

    return final_briefing