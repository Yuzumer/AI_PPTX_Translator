import os
import asyncio
from extractor import extract_text_from_ppt_advanced
from context_generator import generate_context_briefing
from translator import translate_text_elements_in_batch
from reconstructor import reconstruct_presentation


async def run_translation_workflow(input_path, output_folder, user_instructions, status_queue, target_language):
    """
    The main ASYNCHRONOUS engine that runs the entire translation process.
    """
    try:
        status_queue.put(('log', f"Target Language set to: {target_language}"))

        # Phase 1: CPU/Disk bound, so it remains a normal synchronous call
        status_queue.put(('log', "Phase 1: Extracting text from presentation..."))
        extracted_data = extract_text_from_ppt_advanced(input_path)
        if not extracted_data:
            status_queue.put(('log', "ERROR: No text found or file is invalid. Halting."))
            status_queue.put(('finished', None))
            return
        status_queue.put(('log', f"Extraction complete. Found {len(extracted_data)} text elements."))

        # Phase 2: A single API call, can remain synchronous for simplicity
        status_queue.put(('log', "Phase 2: Generating context with AI..."))
        context_summary = generate_context_briefing(extracted_data, user_instructions)
        if not context_summary:
            status_queue.put(('log', "ERROR: Could not generate context. Check API key. Halting."))
            status_queue.put(('finished', None))
            return
        status_queue.put(('log', "Context generation complete."))

        # Phase 3: The I/O-bound part. We MUST 'await' it.
        translated_data = await translate_text_elements_in_batch(extracted_data, context_summary, target_language,
                                                                 status_queue)
        if not translated_data:
            status_queue.put(('log', "ERROR: Translation failed. Halting."))
            status_queue.put(('finished', None))
            return

        # Phase 4: CPU/Disk bound, remains a normal synchronous call
        status_queue.put(('log', "Phase 4: Reconstructing translated presentation..."))
        base_name = os.path.basename(input_path)
        file_name_no_ext, _ = os.path.splitext(base_name)
        output_file_name = f"{file_name_no_ext}_{target_language}.pptx"
        output_path = os.path.join(output_folder, output_file_name)

        reconstruct_presentation(translated_data, input_path, output_path)
        status_queue.put(('log', f"🎉 Success! Your translated presentation is ready:"))
        status_queue.put(('log', f"{output_path}"))

    except Exception as e:
        status_queue.put(('log', f"An unexpected error occurred: {e}"))
    finally:
        # Always signal to the GUI that the process is finished
        status_queue.put(('finished', None))