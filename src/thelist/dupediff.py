import warnings
# Silence specific syntax warnings from third-party libs
warnings.filterwarnings("ignore", category=SyntaxWarning, module="glob2")

import fiftyone as fo
import fiftyone.brain as fob

# --- CONFIG ---
IMAGES_DIR = "/Volumes/Moana/Images/Ladies/"
DATASET_NAME = "ladies_project_v1"

def main():
    # 1. Load the dataset (or create it if missing)
    if DATASET_NAME in fo.list_datasets():
        dataset = fo.load_dataset(DATASET_NAME)
    else:
        print("Loading images (this happens once)...")
        dataset = fo.Dataset.from_images_dir(IMAGES_DIR, name=DATASET_NAME)
        dataset.persistent = True

    print(f"Scanning {len(dataset)} images...")

    # --- LEVEL A: EXACT DUPLICATES ---
    print("Finding exact file duplicates...")
    exact_dupes = fob.compute_exact_duplicates(dataset)
    
    count_exact = 0
    
    # SAFETY CHECK: If it's a flat list of strings, wrap it to match expected format
    if exact_dupes and isinstance(exact_dupes[0], str):
        # This implies all items in this list are duplicates of *something*
        # We'll just treat the whole batch as one group or skip to be safe.
        print(f"Warning: exact_dupes returned a flat list. Skipping auto-tag to prevent errors.")
    else:
        for dupe_group in exact_dupes:
            # Standard List of Lists behavior
            for sample_id in dupe_group[1:]: 
                try:
                    sample = dataset[sample_id]
                    sample.tags.append("delete_exact")
                    sample.save()
                    count_exact += 1
                except KeyError:
                    continue # Skip if ID is weird
            
    print(f"Tagged {count_exact} exact duplicates for deletion.")
    # --- LEVEL B & C: NEAR DUPLICATES (Visual Similarity) ---
    # This detects resized images, format changes (PNG vs JPG), and color grading.
    # We use a threshold of 0.985 (98.5%) for "Safe" and 0.95 (95%) for "Review".
    
    print("Computing visual embeddings (The AI Brain)...")
    # We use 'clip-vit-base32-torch' which is excellent at seeing content, not just pixels.
    fob.compute_similarity(
        dataset, 
        model="clip-vit-base32-torch", 
        brain_key="image_sim"
    )

    print("Identifying near-duplicates...")
    # This finds clusters of images that are >98.5% similar
    near_dupes = fob.compute_near_duplicates(
        dataset, 
        brain_key="image_sim", 
        threshold=0.015 # Distance threshold (1 - 0.985 = 0.015)
    )

    count_near = 0
    for dupe_group in near_dupes.values():
        # dupe_group is a list of (id, distance) tuples.
        # We sort by file size (keep the largest/highest quality one usually)
        # OR just keep the first one found if you don't care.
        
        # Let's get the actual sample objects to check file size
        samples = [dataset[id] for id, dist in dupe_group]
        
        # Sort by file size (descending), so we keep the biggest one
        samples.sort(key=lambda s: s.metadata.size_bytes if s.metadata else 0, reverse=True)
        
        # Keep the first (biggest), tag the rest
        for sample in samples[1:]:
            # Check if we already tagged it as exact
            if "delete_exact" not in sample.tags:
                sample.tags.append("delete_near")
                sample.save()
                count_near += 1

    print(f"Tagged {count_near} near-duplicates (resized/reformatted) for deletion.")

    # --- LAUNCH APP ---
    print("\nDONE. Opening App...")
    print("1. Click the 'filter' icon (funnel) in the sidebar.")
    print("2. Filter by tags: 'delete_exact' or 'delete_near' to verify.")
    
    session = fo.launch_app(dataset)
    session.wait()

if __name__ == "__main__":
    main()