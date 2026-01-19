import os
import csv
import re

# --- CONFIGURATION ---
ROOT_DIR = '/Volumes/Moana/Images/Ladies'
MAP_FILE = 'xIDENT_NAME_map.csv'

# Column Headers in your CSV (Check these match your export!)
COL_NAME = 'NAME'
COL_ID = 'xIDENT'  # Or whatever you named the ID column (e.g., "ID", "xID")

def load_id_map(csv_path):
    """
    Loads the CSV into a dictionary: { "normalized_name": "xID" }
    """
    if not os.path.exists(csv_path):
        print(f"Error: Could not find {csv_path}")
        return {}

    id_map = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get(COL_NAME, '').strip()
            xid = row.get(COL_ID, '').strip()
            
            if name and xid:
                # Normalize key for loose matching (lowercase)
                id_map[name.lower()] = xid
    
    return id_map

def rename_folders(root_path, id_map, dry_run=True):
    print(f"--- STARTING RENAME ({'TEST MODE' if dry_run else 'LIVE MODE'}) ---")
    
    renamed_count = 0
    
    # regex to detect if folder already has an ID (e.g. [xA1B2C])
    # Matches square brackets containing 'x' followed by 5 hex digits
    existing_id_pattern = re.compile(r'\[x[0-9A-F]{5}\]', re.IGNORECASE)

    for root, dirs, files in os.walk(root_path):
        for dirname in dirs:
            
            # 1. Skip if already tagged
            if existing_id_pattern.search(dirname):
                # print(f"[SKIP] Already tagged: {dirname}")
                continue
            
            # 2. Extract "Clean Name" for lookup
            # If folder is "Miley Cyrus (Pop Star)", we look up "Miley Cyrus"
            # We strip trailing tags in parentheses for the lookup key
            clean_name = re.sub(r'\s*\(.*?\)$', '', dirname).strip().lower()
            
            # 3. Lookup
            if clean_name in id_map:
                xid = id_map[clean_name]
                
                # 4. Construct New Name
                # Format: "OriginalName [xIDENT]"
                # We keep the original 'dirname' casing/tags to be safe
                new_dirname = f"{dirname} | {xid}"
                
                full_old_path = os.path.join(root, dirname)
                full_new_path = os.path.join(root, new_dirname)
                
                renamed_count += 1
                
                if dry_run:
                    print(f"[PREVIEW] {dirname}")
                    print(f"       -> {new_dirname}")
                else:
                    try:
                        os.rename(full_old_path, full_new_path)
                        print(f"[RENAMED] {dirname} -> {new_dirname}")
                    except OSError as e:
                        print(f"[ERROR] Could not rename {dirname}: {e}")
            else:
                # Folder name didn't match anyone in the sheet
                # print(f"[SKIP] No match found for: {dirname}")
                pass

    print("-" * 60)
    print(f"Scan complete. {renamed_count} folders {'identified' if dry_run else 'renamed'}.")

# --- EXECUTION ---
# 1. Load the Map
mapping = load_id_map(os.path.join(ROOT_DIR, MAP_FILE))

if mapping:
    print(f"Loaded {len(mapping)} IDs from map.")
    # 2. Run the Rename
    # Set dry_run=True to test first
    rename_folders(ROOT_DIR, mapping, dry_run=True)
else:
    print("Mapping failed to load. Check your CSV file path and headers.")