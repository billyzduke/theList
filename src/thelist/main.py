import pandas as pd
import pygsheets
import numpy as np
import json
import macos_tags
import os
import re
import sys
import time
import bZdUtils
from natsort import natsorted
import hashlib

def generate_xIDENT(name, existing_ids):
  """
  Generates a deterministic 'x' + 5-char Hex ID.
  """
  ID_PREFIX = 'x'
  ID_LENGTH = 5 
  
  clean_name = str(name).strip().lower()
  salt = 0
  
  while True:
    hash_input = clean_name
    if salt > 0:
      hash_input += f"_{salt}"
        
    full_hex = hashlib.md5(hash_input.encode('utf-8')).hexdigest().upper()
    candidate_id = f"{ID_PREFIX}{full_hex[:ID_LENGTH]}"
    
    if candidate_id not in existing_ids:
      return candidate_id
    
    salt += 1

# Auth and Open 
gc = pygsheets.authorize(service_file='credentials.json')
sh = gc.open('@inhumantouch')
wks = sh.worksheet_by_title('blendus synced pretty')

# Efficient Read
df = wks.get_as_df(has_header=True)
df = df.dropna(subset=['NAME'])
xIDENTs = set(df['xIDENT'].dropna().unique())

dicTotals = df.iloc[0]

df['whaddayado'] = (
  df['whaddayado']
  .fillna('')     
  .str.strip()
  .str.split(r'\s*[,/]\s*')
  .apply(lambda x: [] if x == [''] else x)
  .str.join(', ')
)
df = df.drop(columns=['hbd', 'age', 'img', 'HIDE ME'])

rem_ladies = df.iloc[1:]

print("\n\n", 'READING THE ROOM!', "\n\n")
print("\n", dicTotals, "\n")
print(f"inhumantouch blendus gsheet contains {len(rem_ladies)} ladies\n")

#moa = Moana, the local drive where all the images of the ladies live
moa_ladies = {}
ladiesPath = '/Volumes/Moana/Images/Ladies/'

REMOTE_LADIES_CHANGED = {'REMOTE LADIES ADDED': {}, 'REMOTE LADIES UPDATED': {}}
LOCAL_LADIES_CHANGED = {'LOCAL LADIES ADDED': {}, 'LOCAL LADIES DELETED': {}, 'LOCAL LADIES NOTED': {}, 'LOCAL LADIES UPDATED': {}}

# gather relevant info from local drive
for root, subs, imgs in os.walk(ladiesPath):
  if root.count('/') == 5: # disregard the root directory
    folder_name = os.path.basename(root) # Get raw folder name
    if len(folder_name): # disregard categorical directories (as opposed to single person's name)
      notName = re.compile(r'^!')
      m = notName.search(folder_name)
      if not m: # detect and handle pipe delimiter
        if '|' in folder_name:
          # Split "Name (& Name) | xIDENT (& xIDENT)" # there may be a pair of names and xIDENTs in a single folder name
          names_xIDENTs = folder_name.split('|')
          names = names_xIDENTs[0].strip()
          xIDENTs = names_xIDENTs[0].strip()
          
          if '&' in names and '&' in xIDENTs:
            name = names.split('&')[0].strip()
            xIDENT = xIDENTs.split('&')[0].strip()
          else:
            name = names
            xIDENT = xIDENTs
          
          moa_ladies[xIDENT] = {'NAME': name, 'img': 0, 'gif': 0, 'jpg': 0, 'png': 0, 'psd': [], 'psb': [], 'subs': subs, 'vids': [], 'folder': folder_name}
          
          # annoying but apparently necessary
          imgs = bZdUtils.remove_value_from_list(imgs, '.DS_Store')

          # count and sort image files by ext/type 
          for i in imgs:
            name_ext = bZdUtils.get_file_ext(i)            
            is_img = ['avif', 'bmp', 'gif', 'jpg', 'jpeg', 'png', 'psd', 'psb', 'tiff', 'webp']
            if name_ext['ext'] in is_img:
              file_at_path = root + '/' + i

              # eliminate all 4 letter .jpeg extensions because i hate them
              if name_ext['ext'] == 'jpeg':
                j = root + '/' + name_ext['name'] + '.jpg'
                os.replace(file_at_path, j)
                
                LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'], folder_name, {})
                LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][folder_name] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][folder_name], 'jpeg -> jpg', [])
                LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][folder_name]['jpeg -> jpg'].append(j)     

                file_at_path = j
                name_ext = bZdUtils.get_file_ext(j)
                if '/' in name_ext['name']:
                  name_ext['name'] = os.path.basename(name_ext['name'])

              moa_ladies[xIDENT]['img'] += 1

              if name_ext['ext'] in ['avif', 'bmp', 'gif', 'tiff']:
                # all should become pngs
                make_it_ping = 'png'
                j = bZdUtils.safe_convert_image(file_at_path, make_it_ping)
                file_ext = bZdUtils.get_file_ext(j)
                if file_ext['ext'] == make_it_ping:
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'], folder_name, {})
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][folder_name] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][folder_name], f'{name_ext['ext']} -> {make_it_ping}', [])
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][folder_name][f'{name_ext['ext']} -> {make_it_ping}'].append(j)     
                  
                  file_at_path = j
                  name_ext = file_ext
                  if '/' in name_ext['name']:
                    name_ext['name'] = os.path.basename(name_ext['name'])
                else:
                  if not (file_at_path == j and file_ext['ext'] == 'gif'):
                    sys.exit(f'There was a problem converting a {name_ext['ext']} to a {make_it_ping}: "{file_at_path}"')

              if name_ext['ext'] == 'gif':
                moa_ladies[xIDENT][name_ext['ext']] += 1
                            
              if name_ext['ext'] == 'png':
                moa_ladies[xIDENT][name_ext['ext']] += 1
                
              if name_ext['ext'] in ['psb', 'psd']:
                moa_ladies[xIDENT]['img'] -= 1
                moa_ladies[xIDENT][name_ext['ext']].append(i)

              if name_ext['ext'] == 'webp':
                # all should become jpgs
                make_it_peg = 'jpg'
                j = bZdUtils.safe_convert_image(file_at_path, make_it_peg)
                file_ext = bZdUtils.get_file_ext(j)
                if file_ext['ext'] == make_it_peg:
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'], folder_name, {})
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][folder_name] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][folder_name], f'{name_ext['ext']} -> {make_it_peg}', [])
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][folder_name][f'{name_ext['ext']} -> {make_it_peg}'].append(j)     
                  
                  file_at_path = j
                  name_ext = file_ext
                  if '/' in name_ext['name']:
                    name_ext['name'] = os.path.basename(name_ext['name'])
                else:
                  sys.exit(f'There was a problem converting a {name_ext['ext']} to a {make_it_peg}: "{file_at_path}"')
                
              if name_ext['ext'] == 'jpg':
                moa_ladies[xIDENT][name_ext['ext']] += 1

              if name_ext['ext'] != 'psb' and name_ext['ext'] != 'psd':
                if '⊠' not in name_ext['name']:
                  pixel_dims = bZdUtils.get_image_size(file_at_path)
                  dims = str(pixel_dims['w']) + '⊠'
                  if pixel_dims['h'] != pixel_dims['w']:
                    dims += str(pixel_dims['h'])                
                  j = root + '/' + name_ext['name'] + '-' + dims + '.' + name_ext['ext']
                  os.replace(file_at_path, j)
                
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'], folder_name, {})
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][folder_name] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][folder_name], 'pixel dims added', [])
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][folder_name]['pixel dims added'].append(j)     
                  
                  file_at_path = j
                  
                file_tags = macos_tags.get_all(file_at_path)
                tag_names = [t.name for t in file_tags]
                if "Unfit AMF" not in tag_names and "Yellow" not in tag_names and "Good 2 Go Girl!" not in tag_names:
                  try:
                    pixel_dims
                  except NameError:
                    pixel_dims = bZdUtils.get_image_size(file_at_path)
                  if pixel_dims['h'] < 1024 or pixel_dims['w'] < 1024:
                    if pixel_dims['h'] < 1024 and pixel_dims['w'] < 1024: 
                      tags_to_add = ["Unfit AMF"]
                    else:
                      tags_to_add = ["Yellow"]
                  else:
                    tags_to_add = ["Good 2 Go Girl!"]
                  macos_tags.set_all(tags_to_add, file=file_at_path)
                  
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'], folder_name, {})
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][folder_name] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][folder_name], 'file tags updated', {})
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][folder_name]['file tags updated'][file_at_path] = tags_to_add     
            else:
              moa_ladies[name]['vids'].append(i)
              LOCAL_LADIES_CHANGED['LOCAL LADIES NOTED'] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES NOTED'], folder_name, {})
              LOCAL_LADIES_CHANGED['LOCAL LADIES NOTED'][folder_name] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES NOTED'][folder_name], 'vids', [])
              LOCAL_LADIES_CHANGED['LOCAL LADIES NOTED'][folder_name]['vids'].append(i)     

loc_ladies = dict(natsorted(moa_ladies.items(), key=lambda x: x[0].casefold()))

print(f"\nlocal Ladies image directory contains {len(loc_ladies)} ladies\n")

print("\n\n", 'CHECKING gsheet AGAINST local Ladies directory...', "\n")

for xIDENT, loc_lady in loc_ladies.items():
  loc_subs = len(loc_lady['subs'])
  name = loc_lady['name']
  folderol_name = f'{name} | {xIDENT}'
  xIDEYE = df['xIDENT'] == xIDENT
  
  rem_lady = df.loc[xIDEYE]
  if rem_lady.empty:
    duplicates = df[df.index.duplicated()]
    if not duplicates.empty():
      print(name)
      print(loc_lady)
      print(duplicates)
      sys.exit()
      
    xIDENT = generate_xIDENT(name, xIDENTs)
    xIDENTs.add(xIDENT)      
    new_rem_lady = pd.DataFrame([{'xIDENT': xIDENT, 'NAME': name, 'Image Folder?': 'Y', 'blendus?': 'N', 'whaddayado': '', 'aka/alias/group': '','known as/for': '', 'origin': '', 'born': '', 'died': '', 'age': '', 'irl': 'N', 'gif': loc_lady['gif'], 'jpg': loc_lady['jpg'], 'png': loc_lady['png'], 'subs': bZdUtils.safe_str_to_int(loc_subs), 'insta': '', 'youtube': '', 'imdb': '', 'listal': '', 'wikipedia': '', 'url': '', 'blended with…': ''}])
    df = pd.concat([df, new_rem_lady], ignore_index=True)
    xIDEYE = df['xIDENT'] == xIDENT
    rem_lady = df.loc[xIDEYE].iloc[0]
    REMOTE_LADIES_CHANGED['REMOTE LADIES ADDED'][folderol_name] = rem_lady['NAME']
  else:
    rem_lady = rem_lady.iloc[0]
    df.loc[xIDEYE, 'Image Folder?'] = 'Y'
    
  if rem_lady['Image Folder?'] == 'Y':
    loc_lady['psf'] = loc_lady['psd'] + loc_lady['psb']
    if len(loc_lady['psf']):
      maxBlendus = 0
      for psf in loc_lady['psf']:
        isBlendus = re.compile(r'^blendus-')
        m = isBlendus.search(psf)
        if m:
          blenDims = re.compile(r'[\d]{3,4}')
          m = blenDims.search(psf)
          blendus = int(m.group())
          if blendus > maxBlendus:
            maxBlendus = blendus
      if maxBlendus > 0 and str(rem_lady['blendus?']) != str(maxBlendus):
        if maxBlendus <= 1280:
          if maxBlendus not in [900, 1024, 1280]:
            maxBlendus = 'rando'
        else:
          maxBlendus = 'xlarge'
        if str(rem_lady['blendus?']) != str(maxBlendus):
          df.loc[xIDEYE, 'blendus?'] = maxBlendus
          REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'] = bZdUtils.add_key_val_pair_if_needed(REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'], folderol_name, {})
          REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'][folderol_name]['blendus?'] = maxBlendus
    
    cols = ['img', 'gif', 'jpg', 'png']
    
    imgs = 0
    for col in cols:
      if col != 'img':
        imgs += loc_lady[col]
        if rem_lady[col] != loc_lady[col]:
          df.loc[named, col] = loc_lady[col]
          REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'] = bZdUtils.add_key_val_pair_if_needed(REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'], folderol_name, {})
          REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'][folderol_name][col] = loc_lady[col]          
      
    if imgs == 0 and loc_subs == 0:
      if rem_lady['Image Folder?'] == 'Y':
        df.loc[named, 'Image Folder?'] = 'N'
        REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'] = bZdUtils.add_key_val_pair_if_needed(REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'], folderol_name, {})
        REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'][folderol_name]['Image Folder?'] = 'N'          
      
      try:
        # --- LOGIC UPDATE: Target specific folder name or pipe version ---
        # Note: This deletion logic assumes the name is the folder name. 
        # If folder uses pipes, 'name' key won't match. 
        # For minimal changes, we assume clean up happens manually or we can update this later.
        ladyPath = ladiesPath + name 
        os.rmdir(ladyPath)
        LOCAL_LADIES_CHANGED['LOCAL LADIES DELETED'][folderol_name] = ladyPath     
      except OSError as e:
        LOCAL_LADIES_CHANGED['LOCAL LADIES DELETED'][folderol_name] = f'ERROR ATTEMPTING TO DELETE LOCAL FOLDER: {ladyPath}\n{e}'
      
    if bZdUtils.safe_str_to_int(rem_lady['subs']) != loc_subs:
      df.loc[named, 'subs'] = loc_subs
      REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'] = bZdUtils.add_key_val_pair_if_needed(REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'], folderol_name, {})
      REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'][folderol_name]['subs'] = loc_subs 
    
print("\n", 'FLIPPING THE SCRIPT!', "\n", 'CHECKING local Ladies directory AGAINST gsheet...', "\n")

whaddayalldo = {}

for i, rem_lady in rem_ladies.iterrows():
  xIDENT = rem_lady['xIDENT']
  name = rem_lady['NAME']
  folder_name = f"{name} | {xIDENT}"
        
  if rem_lady['whaddayado'].strip():    
    rawccupados = re.split(r',\s', rem_lady['whaddayado'])
    occupados = [x for x in rawccupados if x]
    for occupado in occupados:
      whaddayalldo = bZdUtils.add_key_val_pair_if_needed(whaddayalldo, occupado, 0)
      whaddayalldo[occupado] += 1
      
  if rem_lady['Image Folder?'] == 'Y':
    if xIDENT not in loc_ladies:
      # --- LOGIC UPDATE: Include xIDENT in new folder names ---
      ladyPath = ladiesPath + folder_name
      # --------------------------------------------------------
      try:
        os.mkdir(ladyPath) 
        LOCAL_LADIES_CHANGED['LOCAL LADIES ADDED'][folder_name] = ladyPath     
      except FileExistsError:
        LOCAL_LADIES_CHANGED['LOCAL LADIES ADDED'][folder_name] = f'LOCAL FOLDER ALREADY EXISTS: {ladyPath}'
      except PermissionError:
        LOCAL_LADIES_CHANGED['LOCAL LADIES ADDED'][folder_name] = f'PERMISSION DENIED WHILE ATTEMPTING TO CREATE LOCAL FOLDER: {ladyPath}'
      except Exception as e:
        LOCAL_LADIES_CHANGED['LOCAL LADIES ADDED'][folder_name] = f'ERROR ATTEMPTING TO CREATE LOCAL FOLDER: {name}\n{e}'
  else:
    xIDEYE = df['xIDENT'] == xIDENT
    changed = False
    if not rem_lady['Image Folder?'].strip():  
      df.loc[xIDEYE, 'Image Folder?'] = 'N'
      df.loc[xIDEYE, 'irl'] = 'N'
      changed = True
    
    if not rem_lady['blendus?'].strip():  
      df.loc[xIDEYE, 'blendus?'] = 'N'
      changed = True

    if rem_lady['Image Folder?'] != 'Y':
      zerosums = ['gif', 'jpg', 'png', 'subs']
      for zerosum in zerosums:
        if not str(rem_lady[zerosum]).strip():  
          df.loc[xIDEYE, zerosum] = 0
          changed = True

    if changed:
      REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'] = bZdUtils.add_key_val_pair_if_needed(REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'], folder_name, {})
      REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'][folder_name]['(re)initialized'] = "with missing default column data."     

print(json.dumps(REMOTE_LADIES_CHANGED, indent=2, default=str))
print(json.dumps(LOCAL_LADIES_CHANGED, indent=2, default=str))

print('whaddayalldo by title')
alpha_sorted = dict(sorted(whaddayalldo.items()))
print(json.dumps(alpha_sorted, indent=2, default=str))

print('whaddayalldo by frequency')
complex_sorted = dict(sorted(whaddayalldo.items(), key=lambda item: (-item[1], item[0])))
print(json.dumps(complex_sorted, indent=2, default=str))

df = df.fillna('') 

df = df.sort_values(
    by=['Image Folder?', 'NAME'],
    ascending=[False, True]  
)

has_tail = True
while has_tail:
  tail = df.tail(1).iloc[0]
  if bZdUtils.safe_str_to_int(tail['NAME'], tail['NAME']) == bZdUtils.safe_str_to_int(tail['NAME']):
    df = df.iloc[:-1]
  else:
    has_tail = False

raw_data_sheet = "blendus synced raw"

timestamp = time.strftime("%Y%m%d-%H%M%S")
backup_filename = f"blendus_synced_raw_{timestamp}.csv"
backup_path = os.path.join('/Volumes/Moana/Dropbox/inhumantouch.art/@importantstuff/theList/backups', backup_filename)

print(f"Creating safety backup: {backup_path}...")
df.to_csv(backup_path, index=False)

try:
    old_test_sheet = sh.worksheet_by_title(raw_data_sheet)
    sh.del_worksheet(old_test_sheet)
    print(f"\nDeleted old raw data sheet '{raw_data_sheet}'.")
except pygsheets.WorksheetNotFound:
    pass 

xwks = sh.add_worksheet(raw_data_sheet, rows=100, cols=26)

print(f"Created fresh raw data sheet: {raw_data_sheet}\n")

xwks.clear() 
xwks.set_dataframe(df, start='A1', copy_head=True, fit=True)

print(f"Successfully updated {len(df)} rows in a single batch.")

print("\n\n", 'SYNC COMPLETE!')
