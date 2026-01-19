import inspect
import os
import sys
import unicodedata
from PIL import Image

def normalize_unicode(s):
  """
  Converts NFD (Mac style) to NFC (Web style) so names match.
  """
  if not isinstance(s, str):
    s = str(s)
  return unicodedata.normalize('NFC', s)

def get_file_ext(file_name):
  name_ext = {'name': '', 'ext': ''}
  if isinstance(file_name, str) and len(file_name) > 0 and "." in file_name:
    split = os.path.splitext(file_name)
    name_ext['name'] = split[0]
    name_ext['ext'] = split[1].lower()[1:]
  return name_ext

def get_image_size(file_at_path):
  valid_extensions = ['avif', 'bmp', 'gif', 'jpg', 'png', 'tiff', 'webp']
  pathname_ext = get_file_ext(file_at_path)
  if pathname_ext['ext'] in valid_extensions:
    try:
      # Open the image file
      with Image.open(file_at_path) as img:
        # img.size returns a tuple (width, height)
        width, height = img.size
        # If you need file size in bytes as well:
        # file_size_bytes = os.path.getsize(file_path)
        return {'w': width, 'h': height}            
    except Exception as e:
      sys.exit(f"Error determining image size for: {file_at_path}: {e}")

def safe_convert_image(file_at_path, target_format="png"):
  target_format = target_format.lower()
  try:
    with Image.open(file_at_path) as img:
      # 1. CHECK FOR ANIMATION
      # We use getattr because static images might not have this attribute set
      if getattr(img, "is_animated", False):
        return file_at_path
      # 2. HANDLE PALETTES & COLOR MODES
      # If it is Palette (P) or CMYK, convert to RGB/RGBA to ensure colors match
      # standard photoshop layers and avoid "cannot write mode P as JPEG" errors.
      if img.mode in ('P', 'CMYK', 'RGBA'):
        if target_format == 'jpg':
          # JPEGs cannot handle Alpha, so convert to RGB (removing transparency)
          # Check if it has transparency first to handle the background color nicely
          if img.mode in ('RGBA', 'P'):
            # Create a white background layer to flatten transparency
            # (Change (255, 255, 255) to any other background color if needed)
            img = img.convert("RGBA")
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3]) # 3 is the alpha channel
            img = background
          else:
            img = img.convert('RGB')
        else:
          # For PNGs, we just want standard RGBA (keeps transparency)
          img = img.convert('RGBA')
      # 3. SAVE
      name_ext = get_file_ext(file_at_path)
      new_file_at_path = name_ext['name'] + '.' + target_format
      img.save(new_file_at_path, quality=95)
      # 4. VERIFY & DELETE OLD FILE
      if os.path.exists(new_file_at_path):
        os.remove(file_at_path)
      else:
        sys.exit(f"Error saving converted image file {file_at_path}, original format version preserved.")
      return new_file_at_path
  except Exception as e:
    sys.exit(f"Error converting image file {file_at_path} to {target_format}: {e}")
                    
def line_info():
  # Get the current frame
  frame = inspect.currentframe()
  # Get the caller's frame info
  caller_frame = inspect.getframeinfo(frame.f_back)

  print(f"File: {caller_frame.filename}, Line: {caller_frame.lineno}", "\n")

# Convert string to integer safely in Python
def safe_str_to_int(s, return_on_fail=None):
  """
  Converts a string to an integer with error handling.
  Returns the integer if successful, or return_on_fail value if conversion fails.
  """
  try:
    # Strip whitespace and convert
    return int(str(s).strip())
  except ValueError:
    #print(f"Error: '{s}' is not a valid integer.")
    return return_on_fail

def remove_value_from_list(arr, value):
  """
  Removes all occurrences of 'value' from the list 'arr'.
  Returns the updated list.
  """
  if not isinstance(arr, list):
    #raise TypeError("arr must be a list")
    return arr

  # Check if value exists
  if value not in arr:
    #print(f"Value '{value}' not found in list.")
    return arr

  # Remove all occurrences
  arr = [item for item in arr if item != value]
  #print(f"Value '{value}' removed successfully.")
  return arr

def pretty_dump(d, indent=0):
  for key, value in d.items():
    print('\t' * indent + str(key))
  if isinstance(value, dict):
    pretty_dump(value, indent+1)
  else:
    print('\t' * (indent+1) + str(value))
    
def add_key_val_pair_if_needed(d, k, v):
  if k not in d:
    d[k] = v
  return d
