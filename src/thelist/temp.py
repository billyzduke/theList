import os

ladies_path = '/Volumes/Moana/Images/Ladies/'

# Get all items in the directory
try:
    all_items = os.listdir(ladies_path)
except FileNotFoundError:
    print(f"Could not find path: {ladies_path}")
    all_items = []

# Filter: Must be a directory AND not start with '!'
# We also usually exclude hidden files starting with '.' just in case
folders = [
    item for item in all_items
    if os.path.isdir(os.path.join(ladies_path, item)) 
    and not item.startswith('!') 
    and not item.startswith('.')
]

# Sort by length (descending), then alphabetically for ties
sorted_folders = sorted(folders, key=lambda x: (-len(x), x))

print(f"Found {len(sorted_folders)} folders. Longest to shortest:\n")

for f in sorted_folders:
    print(f"[{len(f)}] {f}")