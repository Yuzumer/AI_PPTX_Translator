import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import json
import math
import asyncio

BATCH_SIZE = 25
MAX_RETRIES = 5
INITIAL_WAIT_TIME = 2


async def translate_single_batch(llm, batch_prompt, batch_num, max_retries, initial_wait, status_queue):
    """An async helper function to translate and handle retries for one batch."""
    for attempt in range(max_retries):
        try:
            ai_response = await llm.ainvoke([HumanMessage(content=batch_prompt)])
            response_content = ai_response.content.strip()
            if response_content.startswith("```json"):
                response_content = response_content[7:-4].strip()
            return json.loads(response_content)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = initial_wait * (2 ** attempt)
                status_queue.put(('log',
                                  f"  - Batch {batch_num} failed (Attempt {attempt + 1}/{max_retries}). Retrying in {wait_time}s..."))
                await asyncio.sleep(wait_time)
            else:
                status_queue.put(
                    ('log', f"  - ERROR: Batch {batch_num} failed after {max_retries} attempts. Skipping."))
                return None


async def translate_text_elements_in_batch(smart_batches, context_briefing, target_language, status_queue):
    status_queue.put(('log', f"--- Starting Phase 3 (Async): Translating to {target_language} ---"))

    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    except Exception as e:
        status_queue.put(('log', f"ERROR: Error initializing AI model: {e}"))
        return None

    # THE FIX: Create a simple list of coroutines, not tuples.
    task_coroutines = []

    for i, batch in enumerate(smart_batches):
        # We need a unique way to map results back. An index is robust.
        # The key in the JSON will now be the item's original index in the flat text_map.
        batch_dict_to_translate = {
            str(original_index): item['original_text']
            for original_index, item in enumerate(batch)
        }

        json_input_string = json.dumps(batch_dict_to_translate, indent=2, ensure_ascii=False)

        translator_prompt = f"""
        You are a native-speaking marketing and business localization expert for {target_language}. 
        Your task is to translate a JSON object of English text snippets into {target_language}.
        Your Core Directives:
        1.  Prioritize Natural Phrasing: The translation must sound like it was written by a native-speaking business professional. Avoid stiff, overly literal, or robotic language. Use natural, idiomatic expressions where appropriate.
        2.  Understand the Context: Use the provided context briefing to understand the document's goal, audience, and tone. The translation's tone must match.
        3.  Handle Jargon Intelligently: If a term is a globally recognized acronym (e.g., "KPI", "ROI", "B2B") or a specific brand/project name mentioned in the user's instructions, preserve it in its original English form unless a common, accepted {target_language} equivalent exists.
        4.  Strict JSON I/O: You will be given a JSON object. You MUST return ONLY a single, valid JSON object with the exact same keys as the input, where the values are the translated text. Do not add any extra text, explanations, or markdown like ```json.
        {context_briefing}
        Translate the values in the following JSON object into {target_language}:
        ---
        {json_input_string}
        ---
        """

        task = translate_single_batch(llm, translator_prompt, i + 1, MAX_RETRIES, INITIAL_WAIT_TIME, status_queue)
        # THE FIX: Append only the coroutine object to the list.
        task_coroutines.append(task)

    status_queue.put(('log', f"Sending {len(task_coroutines)} batches for translation concurrently..."))

    # THE FIX: 'gather' now receives a clean list of coroutines to run.
    results = await asyncio.gather(*task_coroutines)

    final_text_map = []
    total_processed_batches = 0
    # THE FIX: Use zip to cleanly pair the original batches with their results.
    for original_batch, translated_dict in zip(smart_batches, results):
        if translated_dict:
            # Reconstruct the batch with the new translated text
            for i, item in enumerate(original_batch):
                # Use the item's index within the batch as the key
                translated_text = translated_dict.get(str(i))
                if translated_text:
                    item['translated_text'] = translated_text
                else:
                    item['translated_text'] = "ERROR: Key not in response."
        else:
            # Mark the entire failed batch with an error
            for item in original_batch:
                item['translated_text'] = "ERROR: API Call Failed After Retries."

        final_text_map.extend(original_batch)

        total_processed_batches += 1
        progress_percent = (total_processed_batches / len(smart_batches)) * 100
        status_queue.put(('progress', progress_percent))

    status_queue.put(('log', "Async translation complete."))
    return final_text_map