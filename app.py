import os

# Import our custom modules
from extractor import extract_text_from_ppt_advanced
from context_generator import generate_context_briefing
from translator import translate_text_elements_in_batch
from reconstructor import reconstruct_presentation  # <-- Import the final piece


def main():
    """
    The main function to run the entire translation workflow.
    """
    print("--- Starting PowerPoint Translation Application ---")

    # Define file paths and language
    ppt_file = 'sample_deck.pptx'
    target_language = "Japanese"

    # Create a smart output file name
    base_name = os.path.splitext(ppt_file)[0]
    output_file = f"{base_name}_{target_language}.pptx"

    # --- PHASE 1: EXTRACTION ---
    extracted_data = extract_text_from_ppt_advanced(ppt_file)
    if not extracted_data:
        print("\nCould not complete Phase 1. Halting execution.")
        return
    print(f"\n--- Phase 1 Complete: {len(extracted_data)} text elements extracted. ---")

    # --- PHASE 2: CONTEXT GENERATION ---
    context_summary = generate_context_briefing(extracted_data)
    if not context_summary:
        print("\nCould not complete Phase 2. Halting execution.")
        return
    print("\n--- Phase 2 Complete: Context briefing generated successfully. ---")

    # --- PHASE 3: TRANSLATION ---
    translated_data = translate_text_elements_in_batch(extracted_data, context_summary, target_language)
    if not translated_data:
        print("\nCould not complete Phase 3. Halting execution.")
        return
    print("\n--- Phase 3 Complete: All text elements have been translated. ---")

    # --- PHASE 4: RECONSTRUCTION ---
    reconstruct_presentation(translated_data, ppt_file, output_file)

    print(f"\n🎉 Success! Your translated presentation is ready: {output_file}")


# This ensures the main() function is called only when we run app.py
if __name__ == "__main__":
    main()