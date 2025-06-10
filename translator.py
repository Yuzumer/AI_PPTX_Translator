import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import json
import math
import asyncio  # Import asyncio

# --- Configuration for Async Operation ---
BATCH_SIZE = 25
MAX_RETRIES = 5
INITIAL_WAIT_TIME = 2


async def translate_single_batch(llm, batch_prompt, batch_num, max_retries, initial_wait, status_queue):
    """
    An async helper function to translate and handle retries for one single batch.

    Args:
        llm: The initialized LangChain model object.
        batch_prompt (str): The full prompt for this specific batch.
        batch_num (int): The number of the batch (e.g., 1, 2, 3...) for logging.
        max_retries (int): Maximum number of times to retry a failed request.
        initial_wait (int): The starting wait time in seconds for exponential backoff.
        status_queue (queue.Queue): The queue to send status updates to the GUI.

    Returns:
        A dictionary of translated text, or None if it fails after all retries.
    """
    for attempt in range(max_retries):
        try:
            # Use ainvoke for asynchronous call
            ai_response = await llm.ainvoke([HumanMessage(content=batch_prompt)])
            response_content = ai_response.content.strip()

            if response_content.startswith("```json"):
                response_content = response_content[7:-4].strip()

            return json.loads(response_content)  # Success, return the parsed dictionary

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = initial_wait * (2 ** attempt)
                status_queue.put(('log',
                                  f"  - Batch {batch_num} failed (Attempt {attempt + 1}/{max_retries}). Retrying in {wait_time}s..."))
                await asyncio.sleep(wait_time)  # Use asyncio.sleep for non-blocking wait
            else:
                status_queue.put(
                    ('log', f"  - ERROR: Batch {batch_num} failed after {max_retries} attempts. Skipping."))
                return None  # Final failure


async def translate_text_elements_in_batch(text_map, context_briefing, target_language, status_queue):
    """
    Asynchronously translates a list of text elements in concurrent batches.
    """
    status_queue.put(('log', f"--- Starting Phase 3 (Async): Translating to {target_language} ---"))

    try:
        # Using the model you specified for high-throughput translation
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-05-20")
    except Exception as e:
        status_queue.put(('log', f"ERROR: Error initializing AI model: {e}"))
        return None

    tasks = []
    num_batches = math.ceil(len(text_map) / BATCH_SIZE)

    for i in range(num_batches):
        start_index = i * BATCH_SIZE
        end_index = start_index + BATCH_SIZE
        batch = text_map[start_index:end_index]

        batch_dict_to_translate = {str(start_index + j): item['original_text'] for j, item in enumerate(batch)}
        json_input_string = json.dumps(batch_dict_to_translate, indent=2, ensure_ascii=False)

        translator_prompt = f"""
        You are a native-speaking marketing and business localization expert for {target_language}. 
        Your task is to translate a JSON object of English text snippets into {target_language}.

        **Your Core Directives:**
        1.  **Prioritize Natural Phrasing:** The translation must sound like it was written by a native-speaking business professional. Avoid stiff, overly literal, or robotic language. Use natural, idiomatic expressions where appropriate.
        2.  **Understand the Context:** Use the provided context briefing to understand the document's goal, audience, and tone. The translation's tone must match.
        3.  **Handle Jargon Intelligently:** If a term is a globally recognized acronym (e.g., "KPI", "ROI", "B2B") or a specific brand/project name mentioned in the user's instructions, preserve it in its original English form unless a common, accepted {target_language} equivalent exists.
        4.  **Strict JSON I/O:** You will be given a JSON object. You MUST return ONLY a single, valid JSON object with the exact same keys as the input, where the values are the translated text. Do not add any extra text, explanations, or markdown like ```json.

        {context_briefing}

        Translate the values in the following JSON object into {target_language}:
        ---
        {json_input_string}
        ---
        """

        # Create a task for each batch and add it to our list of tasks to run
        task = translate_single_batch(llm, translator_prompt, i + 1, MAX_RETRIES, INITIAL_WAIT_TIME, status_queue)
        tasks.append(task)

    status_queue.put(('log', f"Sending {len(tasks)} batches for translation concurrently..."))
    # Run all tasks at the same time and wait for them all to complete
    results = await asyncio.gather(*tasks)

    total_processed = 0
    for i, translated_batch_dict in enumerate(results):
        if translated_batch_dict:
            for original_index_str, translated_text in translated_batch_dict.items():
                text_map[int(original_index_str)]['translated_text'] = translated_text
        else:
            # Mark the items in the failed batch with an error
            start_index = i * BATCH_SIZE
            end_index = start_index + BATCH_SIZE
            failed_batch = text_map[start_index:end_index]
            for item in failed_batch:
                item['translated_text'] = "ERROR: API Call Failed After Retries."

        total_processed += 1
        progress_percent = (total_processed / num_batches) * 100
        status_queue.put(('progress', progress_percent))

    status_queue.put(('log', "Async translation complete."))
    return text_map