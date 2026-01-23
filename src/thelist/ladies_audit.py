import pygsheets
import pandas as pd
import os
import sys

# --- IMPORT LOCAL UTILS ---
try:
  from . import bZdUtils
except ImportError:
  print("ERROR: Could not import 'bZdUtils'. Make sure bZdUtils.py is in the same directory.")
  sys.exit(1)

# --- CONFIGURATION ---
IMAGES_DIR = '/Volumes/Moana/Images/Ladies/'
SHEET_TITLE = 'blendus synced raw'
CREDENTIALS_FILE = 'credentials.json'

# --- 1. SETUP & LOAD ---
print("--- STARTING DEEP FOLDER AUDIT (NORMALIZED NAMES ONLY) ---")

if not os.path.exists(IMAGES_DIR):
  print(f"ERROR: Local directory not found: {IMAGES_DIR}")
  sys.exit(1)

print("Connecting to Google Sheets...")
try:
  gc = pygsheets.authorize(service_file=CREDENTIALS_FILE)
  sh = gc.open('@inhumantouch')
  wks = sh.worksheet_by_title(SHEET_TITLE)
except Exception as e:
  print(f"Connection Error: {e}")
  sys.exit(1)

print("Fetching sheet data...")
df = wks.get_as_df(has_header=True)
df.columns = [c.strip() for c in df.columns] 

required_cols = ['NAME', 'xIDENT', 'Image Folder?']
for col in required_cols:
  if col not in df.columns:
    print(f"ERROR: Sheet is missing '{col}' column.")
    sys.exit(1)

# --- 2. PARSE SHEET DATA ---
sheet_db = {}

for index, row in df.iterrows():
  # NORMALIZE NAME ONLY
  raw_name = str(row['NAME']).strip()
  if not raw_name: continue
  name = bZdUtils.normalize_unicode(raw_name)
  
  # DO NOT NORMALIZE ID
  raw_id = str(row['xIDENT']).strip()
  if raw_id and raw_id.lower() != 'nan':
    row_id = raw_id # Kept literal
  else:
    row_id = ""
  
  folder_flag = str(row['Image Folder?']).strip().upper()
  expects_folder = folder_flag.startswith('Y')
  
  sheet_db[name] = {
    'id': row_id,
    'expect': expects_folder
  }

print(f"Sheet contains {len(sheet_db)} unique names.")

# --- 3. PARSE DRIVE FOLDERS ---
found_on_drive = {} # Key: (Name, ID), Value: FolderName
malformed_folders = [] 
orphan_folders = [] 

try:
  # Filter: Must be dir, not hidden (.), and NOT starting with (!)
  folder_list = [
      f for f in os.listdir(IMAGES_DIR) 
      if os.path.isdir(os.path.join(IMAGES_DIR, f)) 
      and not f.startswith('.') 
      and not f.startswith('!')
  ]
except OSError as e:
  print(f"Error scanning directory: {e}")
  sys.exit(1)

print(f"Scanning {len(folder_list)} valid local folders...")

for folder in folder_list:
  # Normalizing the folder name string for parsing, 
  # but we need to be careful not to corrupt the ID part if it had special chars (unlikely for IDs)
  # Ideally, we split first, THEN normalize the name part.
  
  if '|' not in folder:
    # Check against Normalized Sheet Names
    # We normalize the whole folder string just to check against names
    if bZdUtils.normalize_unicode(folder).strip() in sheet_db:
      malformed_folders.append(folder)
    else:
      orphan_folders.append(folder)
    continue

  parts = folder.split('|')
  if len(parts) != 2:
    malformed_folders.append(folder)
    continue

  # 1. NAMES part -> Split by '&', strip, NORMALIZE
  raw_names_part = parts[0]
  folder_names = [bZdUtils.normalize_unicode(n.strip()) for n in raw_names_part.split('&')]

  # 2. IDs part -> Split by '&', strip, DO NOT NORMALIZE
  raw_ids_part = parts[1]
  folder_ids = [i.strip() for i in raw_ids_part.split('&')]

  if len(folder_names) != len(folder_ids):
    print(f"⚠️  WARNING: Count mismatch in folder: {folder}")
  
  for name, fid in zip(folder_names, folder_ids):
    found_on_drive[(name, fid)] = folder


# --- 4. RUN AUDIT LOGIC ---

missing_on_drive = []
unexpected_on_drive = []
id_mismatch = []
orphans_with_ids = []

# A. CHECK SHEET AGAINST DRIVE
for name, data in sheet_db.items():
  expected_id = data['id']
  expect_folder = data['expect']
  
  match_found = (name, expected_id) in found_on_drive
  
  if match_found:
    if not expect_folder:
      unexpected_on_drive.append(f"{name} (xIDENT: {expected_id}) found in '{found_on_drive[(name, expected_id)]}'")
    
    del found_on_drive[(name, expected_id)]
    
  else:
    # Check for ID Mismatch
    # We look for the Name in the keys, regardless of ID
    found_alt_ids = [fid for (fname, fid) in found_on_drive if fname == name]
    
    if found_alt_ids:
      for wrong_id in found_alt_ids:
        actual_folder = found_on_drive[(name, wrong_id)]
        id_mismatch.append(f"{name}: Sheet has [{expected_id}], Drive has [{wrong_id}] in folder '{actual_folder}'")
        del found_on_drive[(name, wrong_id)]
        
    elif expect_folder:
      missing_on_drive.append(f"{name} (xIDENT: {expected_id})")

# B. CHECK LEFTOVERS (Orphans)
for (name, fid), folder in found_on_drive.items():
  orphans_with_ids.append(f"{name} | {fid} (in folder: {folder})")


# --- 5. PRINT REPORT ---

print("\n" + "="*50)
print("DEEP AUDIT REPORT")
print("="*50)

errors_found = False

if malformed_folders:
  errors_found = True
  print(f"\n🚫 MALFORMED FOLDERS ({len(malformed_folders)})")
  print("   (Folder matches a Name, but is missing '|' and ID)")
  for f in sorted(malformed_folders):
    print(f"   - {f}")

if id_mismatch:
  errors_found = True
  print(f"\n≠  ID MISMATCHES ({len(id_mismatch)})")
  print("   (Name found, but Folder ID does not match Sheet xIDENT)")
  for err in sorted(id_mismatch):
    print(f"   - {err}")

if missing_on_drive:
  errors_found = True
  print(f"\n❌ MISSING ON DRIVE ({len(missing_on_drive)})")
  print("   (Sheet says 'Y', but no matching folder found)")
  for err in sorted(missing_on_drive):
    print(f"   - {err}")

if unexpected_on_drive:
  errors_found = True
  print(f"\n⚠️  UNEXPECTED FOLDERS ({len(unexpected_on_drive)})")
  print("   (Folder exists & valid, but Sheet says 'N' or blank)")
  for err in sorted(unexpected_on_drive):
    print(f"   - {err}")

if orphans_with_ids:
  errors_found = True
  print(f"\n❓ ORPHAN FOLDERS (With IDs) ({len(orphans_with_ids)})")
  print("   (Valid format, but Name not found in Sheet)")
  for err in sorted(orphans_with_ids):
    print(f"   - {err}")

if orphan_folders:
  errors_found = True
  print(f"\n🗑️  UNKNOWN / LOOSE FOLDERS ({len(orphan_folders)})")
  print("   (No pipe delimiter, Name not in Sheet)")
  for f in sorted(orphan_folders):
    print(f"   - {f}")

if not errors_found:
  print("\n✅ PERFECT SYNC. All folders are properly named, coded, and accounted for.")

print("\n" + "="*50)