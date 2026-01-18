import os
import re
import csv
import datetime
import time

# --- CONFIGURATION ---
ROOT_DIR = '/Volumes/Moana/Dropbox/inhumantouch.art/'
OUTPUT_FILE = 'extracted_blends.csv'

# MJ Version Timeline (Launch Dates)
MJ_VERSIONS = [
    (datetime.date(2025, 4, 3), "7.0"),
    (datetime.date(2024, 7, 30), "6.1"),
    (datetime.date(2023, 12, 21), "6.0"),
    (datetime.date(2023, 6, 22), "5.2"),
    (datetime.date(2023, 5, 3), "5.1"),
    (datetime.date(2023, 3, 15), "5.0"),
    (datetime.date(2022, 11, 5), "4.0"),
    (datetime.date(2022, 7, 25), "3.0")
]

def get_mj_version_from_date(file_timestamp):
    """Determines MJ version based on file creation date."""
    file_date = datetime.date.fromtimestamp(file_timestamp)
    for launch_date, version in MJ_VERSIONS:
        if file_date >= launch_date:
            return version
    return "3.0" # Fallback for very old files

def parse_filename(filename):
    """
    Extracts metadata from filename.
    Returns None if it doesn't look like a valid blend file.
    """
    # 1. Names: Look for CamelCase names separated by plus signs
    # Regex: Start of string, letters only, must contain at least one plus
    name_match = re.search(r'^([a-zA-Z]+(?:\+[a-zA-Z]+)+)', filename)
    if not name_match:
        return None
    raw_names = name_match.group(1)
    
    # 2. Hex Code: Look for 6 hex chars (capitalized by previous script)
    # We ignore if it's part of a word, so we look for boundaries
    hex_match = re.search(r'(?<![A-Z0-9])([0-9A-F]{6})(?![A-Z0-9])', filename)
    hex_code = hex_match.group(1) if hex_match else ""

    # 3. Rating & "Chosen" Status
    # Look for 2 digits 00-13 surrounded by delimiters (+, -, or start/end)
    # We capture the delimiters to check for the "Chosen" (+) mark
    rating_match = re.search(r'([+\-])(0[0-9]|1[0-3])([+\-])', filename)
    
    rating = 0
    is_chosen = False
    
    if rating_match:
        rating = int(rating_match.group(2))
        # If either side is a '+', it's a chosen file
        if rating_match.group(1) == '+' or rating_match.group(3) == '+':
            is_chosen = True
    
    # 4. A/B Batch
    batch = "A" # Default
    if "-B-" in filename or "+B-" in filename or "-B+" in filename:
        batch = "B"
    
    # 5. Explicit MJ Version (e.g. Mj5.2)
    mj_match = re.search(r'Mj([0-9]\.?[0-9]?)', filename, re.IGNORECASE)
    explicit_version = mj_match.group(1) if mj_match else None

    return {
        "names": raw_names,
        "hex": hex_code,
        "rating": rating,
        "is_chosen": is_chosen,
        "batch": batch,
        "explicit_version": explicit_version,
        "filename": filename
    }

def process_directory(root_path):
    print(f"Scanning {root_path}...")
    
    # Dictionary to Group Attempts: 
    # Key = "Name1, Name2" (Sorted) -> Value = List of file data
    blend_groups = {} 
    
    count = 0
    
    for root, dirs, files in os.walk(root_path):
        for file in files:
            if file.startswith('.') or not file.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue
                
            data = parse_filename(file)
            if data:
                # Get file date for versioning
                full_path = os.path.join(root, file)
                try:
                    # Try birthtime (Mac), fall back to mtime
                    stat = os.stat(full_path)
                    creation_time = getattr(stat, 'st_birthtime', stat.st_mtime)
                except OSError:
                    # Fallback if stat fails (e.g., permissions issue)
                    creation_time = os.path.getmtime(full_path)                
                data['creation_time'] = creation_time
                data['date_str'] = datetime.datetime.fromtimestamp(creation_time).strftime('%Y-%m-%d')
                
                # Create a unique key for the group (alphabetized names)
                # "Zendaya+Sydney" and "Sydney+Zendaya" should group together
                name_list = data['names'].split('+')
                name_list.sort()
                group_key = ", ".join(name_list)
                
                if group_key not in blend_groups:
                    blend_groups[group_key] = []
                blend_groups[group_key].append(data)
                count += 1

    print(f"Found {count} candidate files. Grouping and filtering...")
    
    # Now, pick the winner for each group
    final_rows = []
    
    for names, candidates in blend_groups.items():
        # Sort candidates to find the "Best"
        # Logic: 
        # 1. Is Chosen (True > False)
        # 2. Rating (High > Low)
        # 3. Batch (B > A)
        
        candidates.sort(key=lambda x: (
            x['is_chosen'],      # Primary: Has '+' marker
            x['rating'],         # Secondary: Higher score
            x['batch'] == 'B'    # Tertiary: B preferred over A
        ), reverse=True)
        
        winner = candidates[0]
        
        # Determine Final MJ Version
        version = winner['explicit_version']
        if not version:
            version = get_mj_version_from_date(winner['creation_time'])
            
        # Format names (Split CamelCase if needed, but for now keeping Raw as requested)
        # The user requested "firstNameLastName1+...", so we provide that.
        # But for the sheet, comma separated is usually better. 
        # Let's give the comma separated version in the CSV for easy pasting.
        
        # We need to split "SydneySweeney" -> "Sydney Sweeney"
        # Regex: Look for Capital letter that is NOT at the start
        formatted_names_list = []
        for raw_n in names.split(", "):
            # Insert space before capitals, ignoring the first char
            spaced_name = re.sub(r'(?<!^)(?=[A-Z])', ' ', raw_n)
            formatted_names_list.append(spaced_name)
        
        formatted_names = ", ".join(formatted_names_list)

        final_rows.append({
            'blendees': formatted_names,
            'hexcode': winner['hex'],
            'date': winner['date_str'],
            'MJv': version,
            'best': winner['rating'],
            'filename': winner['filename'] # kept for reference
        })

    # Write to CSV
    print(f"Exporting {len(final_rows)} unique blends to {OUTPUT_FILE}...")
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['hexcode', 'blendees', 'date', 'MJv', 'best', 'filename'])
        writer.writeheader()
        for row in final_rows:
            writer.writerow(row)
            
    print("Done!")

# Run it
process_directory(ROOT_DIR)