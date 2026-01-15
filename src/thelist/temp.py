import os

def find_blendus_folders():
  girlsPath = '/Volumes/Moana/Dropbox/inhumantouch.art/'
  
  if not os.path.exists(girlsPath):
    print(f"Error: The path '{girlsPath}' does not exist.")
    return

  print(f"Scanning: {girlsPath}...\n")
  
  match_count = 0
  
  # os.walk yields a 3-tuple (current_root, directories, files)
  for root, dirs, files in os.walk(girlsPath):
    for dirname in dirs:
      # Check for "blendus" OR "+"
      if "blendus" in dirname.lower() or "+" in dirname:
        full_path = os.path.join(root, dirname)
        print(full_path)
        match_count += 1
        
  print(f"\nDone. Found {match_count} folders.")

if __name__ == "__main__":
  find_blendus_folders()