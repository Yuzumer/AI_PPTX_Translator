import os
import asyncio
from extractor import extract_text_from_ppt_advanced
from context_generator import generate_context_briefing
from batcher import create_smart_batches  # <-- Import our new module
from translator import translate_text_elements_in_batch
from reconstructor import reconstruct_presentation


async def run_translation_workflow(input_path, output_folder, user_instructions, status_queue, target_language):
    """
    The main ASYNCHRONOUS engine, now using the Smart Batching strategy.
    """
    output_path = ""
    try:
        status_queue.put(('log', f"Target Language set to: {target_language}"))

        status_queue.put(('log', "Phase 1: Extracting text from presentation..."))
        extracted_data = extract_text_from_ppt_advanced(input_path)
        if not extracted_data:
            # ... (error handling) ...
            return
        status_queue.put(('log', f"Extraction complete. Found {len(extracted_data)} text elements."))

        status_queue.put(('log', "Phase 2: Generating context with AI..."))
        context_summary = generate_context_briefing(extracted_data, user_instructions)
        if not context_summary:
            # ... (error handling) ...
            return
        status_queue.put(('log', "Context generation complete."))

        # --- NEW STEP: SMART BATCHING ---
        status_queue.put(('log', "Creating smart batches for translation..."))
        # The ideal batch size is defined in the translator module
        from translator import BATCH_SIZE
        smart_batches = create_smart_batches(extracted_data, BATCH_SIZE)
        status_queue.put(('log', f"Created {len(smart_batches)} context-aware batches."))

        # Pass the pre-made batches to the translator
        translated_data = await translate_text_elements_in_batch(smart_batches, context_summary, target_language,
                                                                 status_queue)
        if not translated_data:
            # ... (error handling) ...
            return

        status_queue.put(('log', "Phase 4: Reconstructing translated presentation..."))
        base_name = os.path.basename(input_path)
        file_name_no_ext, _ = os.path.splitext(base_name)
        output_file_name = f"{file_name_no_ext}_{target_language}.pptx"
        output_path = os.path.join(output_folder, output_file_name)

        # The final text_map is returned by the translator
        reconstruct_presentation(translated_data, input_path, output_path)
        status_queue.put(('log', f"🎉 Success! Your translated presentation is ready:"))
        status_queue.put(('log', f"{output_path}"))

    except Exception as e:
        status_queue.put(('log', f"An unexpected error occurred: {e}"))
    finally:
        status_queue.put(('finished', output_path))