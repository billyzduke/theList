import os
import re

def clean_filenames(root_path, dry_run=True):
    """
    Walks through a directory to:
    1. Capitalize distinct 6-digit hex codes (e.g., 'a1b2c3' -> 'A1B2C3').
       - Ignores codes that are already capitalized.
    2. Normalize .jpeg extensions to .jpg.
    
    :param root_path: The directory to search.
    :param dry_run: If True, only prints changes. If False, renames files.
    """
    
    if not os.path.exists(root_path):
        print(f"Error: Directory not found: {root_path}")
        return

    # Regex 1: The Hex Code Finder
    # Matches exactly 6 hex characters (0-9, A-F) NOT surrounded by other letters/numbers.
    hex_pattern = re.compile(r'(?<![0-9a-zA-Z])([0-9a-fA-F]{6})(?![0-9a-zA-Z])')

    # Regex 2: The Extension Finder
    # Matches .jpeg at the end of the file (Case Insensitive)
    jpeg_pattern = re.compile(r'\.jpeg$', re.IGNORECASE)

    print(f"--- STARTING SCAN ---")
    print(f"Target: {root_path}")
    print(f"Mode: {'TEST (Dry Run)' if dry_run else 'LIVE (Renaming)'}")
    print("-" * 60)

    matches_found = 0

    for root, dirs, files in os.walk(root_path):
        for filename in files:
            if filename.startswith('.'):
                continue

            # Start with the original name
            new_filename = filename

            # 1. Fix Hex Codes (Capitalize)
            # If the code is already ALL CAPS (e.g. A1B2C3), .upper() changes nothing,
            # so the filename remains strictly identical.
            new_filename = hex_pattern.sub(lambda m: m.group(0).upper(), new_filename)

            # 2. Fix Extension (.jpeg -> .jpg)
            new_filename = jpeg_pattern.sub('.jpg', new_filename)

            # 3. Only process if something actually changed
            if new_filename != filename:
                matches_found += 1
                full_old_path = os.path.join(root, filename)
                full_new_path = os.path.join(root, new_filename)

                if dry_run:
                    print(f"[PREVIEW] {filename}")
                    print(f"       -> {new_filename}")
                else:
                    try:
                        # Safety: Don't overwrite if the target already exists
                        if os.path.exists(full_new_path):
                            print(f"[SKIP] Target already exists: {new_filename}")
                        else:
                            os.rename(full_old_path, full_new_path)
                            print(f"[RENAMED] {filename} -> {new_filename}")
                    except OSError as e:
                        print(f"[ERROR] Could not rename {filename}: {e}")

    print("-" * 60)
    if matches_found == 0:
        print("No files found requiring updates.")
    else:
        print(f"Scan complete. {matches_found} files {'identified' if dry_run else 'processed'}.")

# --- CONFIGURATION ---
target_dir = '/Volumes/Moana/Dropbox/inhumantouch.art/'

# 1. Run with dry_run=True first to verify the list.
# 2. Change to dry_run=False to apply the changes.
clean_filenames(target_dir, dry_run=True)