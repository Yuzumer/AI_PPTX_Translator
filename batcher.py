from itertools import groupby


def create_smart_batches(text_map, batch_size):
    """
    Creates context-aware batches. It tries to keep slides together
    without exceeding the batch size, and splits very large slides.

    Args:
        text_map (list): The flat list of text elements from the extractor.
        batch_size (int): The ideal target size for a batch.

    Returns:
        list: A list of lists, where each inner list is a batch of text elements.
    """
    if not text_map:
        return []

    final_batches = []

    # Step 1: Group all text elements by their slide index.
    # This gives us a list of lists, where each inner list is a full slide.
    slides_as_groups = [list(g) for _, g in groupby(text_map, lambda x: x['slide_index'])]

    current_batch = []
    for slide_group in slides_as_groups:
        # If a single slide is much larger than our batch size, split it.
        if len(slide_group) > batch_size * 1.5:
            # First, if the current_batch has items, seal it off.
            if current_batch:
                final_batches.append(current_batch)
                current_batch = []

            # Split the large slide into chunks and add each as a separate batch.
            for i in range(0, len(slide_group), batch_size):
                final_batches.append(slide_group[i:i + batch_size])
            continue  # Move to the next slide group

        # If adding the next slide would overflow the current batch, seal the current one.
        if len(current_batch) + len(slide_group) > batch_size:
            if current_batch:
                final_batches.append(current_batch)
            current_batch = slide_group
        else:
            # Otherwise, add the slide's elements to the current batch.
            current_batch.extend(slide_group)

    # Don't forget the last batch!
    if current_batch:
        final_batches.append(current_batch)

    return final_batches