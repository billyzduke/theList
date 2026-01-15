import pandas as pd
import pygsheets
import numpy as np
import json
import macos_tags
import os
import re
import sys
import bZdUtils
from natsort import natsorted

include_og = False # reserved for future fixing of my own fuckups (retrieves data from original manually updated sheet)

# Auth and Open 
gc = pygsheets.authorize(service_file='credentials.json')
sh = gc.open('@inhumantouch')
wks = sh.worksheet_by_title('blendus synced pretty')
if include_og:
  ogwks = sh.worksheet_by_title('blendus og')
  ogdf = ogwks.get_as_df(has_header=True)
  og_rem_ladies = ogdf.iloc[2:]

# Efficient Read
# This reads the whole sheet into a pandas dataframe in one go. 
# 'has_header=True' uses the first row as column names.
df = wks.get_as_df(has_header=True)
df = df.dropna(subset=['NAME'])

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
  # disregard the root directory
  if root.count('/') == 5:
    name = os.path.basename(root)
    # disregard categorical directories (as opposed to single person's name)
    if len(name):
      notName = re.compile(r'^!')
      m = notName.search(name)
      # detect and disregard combination folders with multiple names
      if not m:
        multiNames = re.compile(r' & ')
        m = multiNames.search(name)
        if m: 
          print('LOCAL COMBO FOLDER DETECTED (AND BYPASSED):', name)
        else:
          # congrats, it's one lady's name
          # proceed
          
          # name = name.encode().decode('utf-8')    
          moa_ladies[name] = {'img': 0, 'gif': 0, 'jpg': 0, 'png': 0, 'psd': [], 'psb': [], 'subs': subs, 'vids': []}
          
          # annoying but apparently necessary, even though I cannot even see these where they are supposedly showing up
          imgs = bZdUtils.remove_value_from_list(imgs, '.DS_Store')
          #print(imgs)   

          # count and sort image files by ext/type 
          for i in imgs:
            name_ext = bZdUtils.get_file_ext(i)            
            is_img = ['avif', 'bmp', 'gif', 'jpg', 'jpeg', 'png', 'psd', 'psb', 'tiff', 'webp']
            if name_ext['ext'] in is_img:
              file_at_path = root + '/' + i

              # eliminate all 4 letter .jpeg extensions because i hate them
              if name_ext['ext'] == 'jpeg':
                j = root + '/' + name_ext['name'] + '.jpg'
                #print(j)
                os.replace(file_at_path, j)
                
                LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'], name, {})
                LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][name] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][name], 'jpeg -> jpg', [])
                LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][name]['jpeg -> jpg'].append(j)     
                #print(json.dumps(LOCAL_LADIES_CHANGED, indent=2, default=str))

                file_at_path = j
                name_ext = bZdUtils.get_file_ext(j)
                if '/' in name_ext['name']:
                  name_ext['name'] = os.path.basename(name_ext['name'])

              moa_ladies[name]['img'] += 1

              if name_ext['ext'] in ['avif', 'bmp', 'gif', 'tiff']:
                # all should become pngs
                make_it_ping = 'png'
                j = bZdUtils.safe_convert_image(file_at_path, make_it_ping)
                file_ext = bZdUtils.get_file_ext(j)
                if file_ext['ext'] == make_it_ping:
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'], name, {})
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][name] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][name], f'{name_ext['ext']} -> {make_it_ping}', [])
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][name][f'{name_ext['ext']} -> {make_it_ping}'].append(j)     
                  
                  file_at_path = j
                  name_ext = file_ext
                  if '/' in name_ext['name']:
                    name_ext['name'] = os.path.basename(name_ext['name'])
                else:
                  if not (file_at_path == j and file_ext['ext'] == 'gif'):
                    sys.exit(f'There was a problem converting a {name_ext['ext']} to a {make_it_ping}: "{file_at_path}"')

              if name_ext['ext'] == 'gif':
                # there might be some animated ones we want to keep
                moa_ladies[name][name_ext['ext']] += 1
                            
              if name_ext['ext'] == 'png':
                moa_ladies[name][name_ext['ext']] += 1
                
              if name_ext['ext'] in ['psb', 'psd']:
                moa_ladies[name]['img'] -= 1
                moa_ladies[name][name_ext['ext']].append(i)

              if name_ext['ext'] == 'webp':
                # all should become jpgs
                make_it_peg = 'jpg'
                j = bZdUtils.safe_convert_image(file_at_path, make_it_peg)
                file_ext = bZdUtils.get_file_ext(j)
                if file_ext['ext'] == make_it_peg:
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'], name, {})
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][name] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][name], f'{name_ext['ext']} -> {make_it_peg}', [])
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][name][f'{name_ext['ext']} -> {make_it_peg}'].append(j)     
                  
                  file_at_path = j
                  name_ext = file_ext
                  if '/' in name_ext['name']:
                    name_ext['name'] = os.path.basename(name_ext['name'])
                else:
                  sys.exit(f'There was a problem converting a {name_ext['ext']} to a {make_it_peg}: "{file_at_path}"')
                
              if name_ext['ext'] == 'jpg':
                moa_ladies[name][name_ext['ext']] += 1

              if name_ext['ext'] != 'psb' and name_ext['ext'] != 'psd':
                # add image pixel size dimensions to file name, because it just makes things easier for me
                # and most of these will never change size, if they do, another upscaled version will be created
                if '⊠' not in name_ext['name']:
                  pixel_dims = bZdUtils.get_image_size(file_at_path)
                  #print(file_at_path, pixel_dims)
                  dims = str(pixel_dims['w']) + '⊠'
                  if pixel_dims['h'] != pixel_dims['w']:
                    dims += str(pixel_dims['h'])                
                  j = root + '/' + name_ext['name'] + '-' + dims + '.' + name_ext['ext']
                  os.replace(file_at_path, j)
                
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'], name, {})
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][name] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][name], 'pixel dims added', [])
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][name]['pixel dims added'].append(j)     
                  
                  file_at_path = j
                  
                file_tags = macos_tags.get_all(file_at_path)
                tag_names = [t.name for t in file_tags]
                #print(file_at_path, tag_names)
                if "Unfit AMF" not in tag_names and "Yellow" not in tag_names and "Good 2 Go Girl!" not in tag_names:
                  # while we're at it, let's tag the images relative to the 1024 pixel squared desired minimum for blending
                  # yeah I know, it doesn't take into account how big the face is framed within the image, but it's a general rule of thumb that below 1024, shit is going to get useless fast regardless of how close-up it is
                  try:
                    # Try to access the variable
                    pixel_dims
                  except NameError:
                    # If it doesn't exist, create it
                    pixel_dims = bZdUtils.get_image_size(file_at_path)
                  if pixel_dims['h'] < 1024 or pixel_dims['w'] < 1024:
                    if pixel_dims['h'] < 1024 and pixel_dims['w'] < 1024: 
                      tags_to_add = ["Unfit AMF"]
                    else:
                      tags_to_add = ["Yellow"]
                  else:
                    tags_to_add = ["Good 2 Go Girl!"]
                  macos_tags.set_all(tags_to_add, file=file_at_path)
                  
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'], name, {})
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][name] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][name], 'file tags updated', {})
                  LOCAL_LADIES_CHANGED['LOCAL LADIES UPDATED'][name]['file tags updated'][file_at_path] = tags_to_add     
            else:
              moa_ladies[name]['vids'].append(i)
              LOCAL_LADIES_CHANGED['LOCAL LADIES NOTED'] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES NOTED'], name, {})
              LOCAL_LADIES_CHANGED['LOCAL LADIES NOTED'][name] = bZdUtils.add_key_val_pair_if_needed(LOCAL_LADIES_CHANGED['LOCAL LADIES NOTED'][name], 'vids', [])
              LOCAL_LADIES_CHANGED['LOCAL LADIES NOTED'][name]['vids'].append(i)     

loc_ladies = dict(natsorted(moa_ladies.items(), key=lambda x: x[0].casefold()))
# print(loc_ladies)

print(f"\nlocal Ladies image directory contains {len(loc_ladies)} ladies\n")

# first, update the gsheet with local changes
print("\n\n", 'CHECKING gsheet AGAINST local Ladies directory...', "\n")


# loop thru local ladies
for name, loc_lady in loc_ladies.items():
  loc_subs = len(loc_lady['subs'])
  named = df['NAME'] == name
  
  # is lady in remote records?
  rem_lady = df.loc[named]
  # if remote record does not already exist, add new row to the gsheet
  if rem_lady.empty:
    duplicates = df[df.index.duplicated()]
    if not duplicates.empty():
      print(name)
      print(loc_lady)
      print(duplicates)
      sys.exit()
      
    new_rem_lady = pd.DataFrame([{'NAME': name, 'Image Folder?': 'Y', 'blendus?': 'N', 'whaddayado': '', 'aka/alias/group': '','known as/for': '', 'origin': '', 'born': '', 'died': '', 'age': '', 'irl': 'N', 'gif': loc_lady['gif'], 'jpg': loc_lady['jpg'], 'png': loc_lady['png'], 'subs': bZdUtils.safe_str_to_int(loc_subs), 'insta': '', 'youtube': '', 'imdb': '', 'listal': '', 'wikipedia': '', 'url': '', 'blended with…': ''}])
    df = pd.concat([df, new_rem_lady], ignore_index=True)
    # verify addition of new remote lady to dataframe
    named = df['NAME'] == name
    rem_lady = df.loc[named].iloc[0]
    REMOTE_LADIES_CHANGED['REMOTE LADIES ADDED'][name] = rem_lady['NAME']
  else:
    rem_lady = rem_lady.iloc[0]
    rem_lady.drop(columns=['hbd', 'img'])
    df.loc[named, 'Image Folder?'] = 'Y'

  #print('REMOTE:', name, rem_lady)
  # if name.startswith("Bj"):
  #   print('LOCAL:', name, loc_lady, "\n") # copy and paste name from here if mismatch due to special characters
  #   sys.exit()
    
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
          df.loc[named, 'blendus?'] = maxBlendus
          REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'] = bZdUtils.add_key_val_pair_if_needed(REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'], name, {})
          REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'][name]['blendus?'] = maxBlendus
    
    cols = ['img', 'gif', 'jpg', 'png']
    
    # for col in cols:
    #   df.loc[named, col] = int(rem_lady[col]) if rem_lady[col] else 0
    
    imgs = 0
    for col in cols:
      #print (name, col)
      if col != 'img':
        imgs += loc_lady[col]
        if rem_lady[col] != loc_lady[col]:
          df.loc[named, col] = loc_lady[col]
          REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'] = bZdUtils.add_key_val_pair_if_needed(REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'], name, {})
          REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'][name][col] = loc_lady[col]          
      
    if imgs == 0 and loc_subs == 0:
      if rem_lady['Image Folder?'] == 'Y':
        df.loc[named, 'Image Folder?'] = 'N'
        REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'] = bZdUtils.add_key_val_pair_if_needed(REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'], name, {})
        REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'][name]['Image Folder?'] = 'N'          
      
      try:
        ladyPath = ladiesPath + name
        os.rmdir(ladyPath)
        LOCAL_LADIES_CHANGED['LOCAL LADIES DELETED'][name] = ladyPath     
      except OSError as e:
        LOCAL_LADIES_CHANGED['LOCAL LADIES DELETED'][name] = f'ERROR ATTEMPTING TO DELETE LOCAL FOLDER: {ladyPath}\n{e}'
      
    if bZdUtils.safe_str_to_int(rem_lady['subs']) != loc_subs:
      df.loc[named, 'subs'] = loc_subs
      REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'] = bZdUtils.add_key_val_pair_if_needed(REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'], name, {})
      REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'][name]['subs'] = loc_subs 
    
print("\n", 'FLIPPING THE SCRIPT!', "\n", 'CHECKING local Ladies directory AGAINST gsheet...', "\n")

whaddayalldo = {}

for i, rem_lady in rem_ladies.iterrows():
  name = rem_lady['NAME']
  
  if include_og:
    ognamed = ogdf['NAME'] == name
    og_rem_lady = ogdf.loc[ognamed]
    
    if not og_rem_lady.empty:
      named = df['NAME'] == name

      og_cols = ['insta', 'youtube', 'imdb', 'listal', 'wikipedia', 'bandcamp', 'spotify', 'url', 'blended with…' ]
      for og_col in og_cols:
        df.loc[named, og_col] = ''

      og_rem_lady = og_rem_lady.iloc[0]
      for og_col in og_cols:
        if len(og_rem_lady[og_col]) > 0:
          df.loc[named, og_col] = og_rem_lady[og_col]
      rem_lady = df.loc[named].iloc[0]
      
  if rem_lady['whaddayado'].strip():    
    rawccupados = re.split(r',\s', rem_lady['whaddayado'])
    occupados = [x for x in rawccupados if x]
    for occupado in occupados:
      whaddayalldo = bZdUtils.add_key_val_pair_if_needed(whaddayalldo, occupado, 0)
      whaddayalldo[occupado] += 1
      
  if rem_lady['Image Folder?'] == 'Y':
    if name not in loc_ladies:
      ladyPath = ladiesPath + name
      try:
        os.mkdir(ladyPath) # Creates a single directory
        LOCAL_LADIES_CHANGED['LOCAL LADIES ADDED'][name] = ladyPath     
      except FileExistsError:
        LOCAL_LADIES_CHANGED['LOCAL LADIES ADDED'][name] = f'LOCAL FOLDER ALREADY EXISTS: {ladyPath}'
      except PermissionError:
        LOCAL_LADIES_CHANGED['LOCAL LADIES ADDED'][name] = f'PERMISSION DENIED WHILE ATTEMPTING TO CREATE LOCAL FOLDER: {ladyPath}'
      except Exception as e:
        LOCAL_LADIES_CHANGED['LOCAL LADIES ADDED'][name] = f'ERROR ATTEMPTING TO CREATE LOCAL FOLDER: {name}\n{e}'
  else:
    named = df['NAME'] == name
    changed = False
    if not rem_lady['Image Folder?'].strip():  
      df.loc[named, 'Image Folder?'] = 'N'
      df.loc[named, 'irl'] = 'N'
      changed = True
    
    if not rem_lady['blendus?'].strip():  
      df.loc[named, 'blendus?'] = 'N'
      changed = True

    if rem_lady['Image Folder?'] != 'Y':
      zerosums = ['gif', 'jpg', 'png', 'subs']
      for zerosum in zerosums:
        if not str(rem_lady[zerosum]).strip():  
          df.loc[named, zerosum] = 0
          changed = True

    if changed:
      REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'] = bZdUtils.add_key_val_pair_if_needed(REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'], name, {})
      REMOTE_LADIES_CHANGED['REMOTE LADIES UPDATED'][name]['(re)initialized'] = "with missing default column data."     

print(json.dumps(REMOTE_LADIES_CHANGED, indent=2, default=str))
print(json.dumps(LOCAL_LADIES_CHANGED, indent=2, default=str))

print('whaddayalldo by title')
alpha_sorted = dict(sorted(whaddayalldo.items()))
print(json.dumps(alpha_sorted, indent=2, default=str))

print('whaddayalldo by frequency')
complex_sorted = dict(sorted(whaddayalldo.items(), key=lambda item: (-item[1], item[0])))
print(json.dumps(complex_sorted, indent=2, default=str))

# Handling NaNs
# Google Sheets API throws errors if you try to upload NaN/Infinity. 
# You MUST replace them with empty strings or zeros.
df = df.fillna('') 
#FutureWarning: Downcasting object dtype arrays on .fillna, .ffill, .bfill is deprecated and will change in a future version. Call result.infer_objects(copy=False) instead. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`

# Date Formatting: Pandas sometimes converts dates to timestamps that look ugly in Sheets. Convert date columns to strings in Python before uploading to preserve the format.
#df['date'] = df['date'].astype(str)

df = df.sort_values(
    by=['Image Folder?', 'NAME'],
    ascending=[False, True]  # True = Ascending, False = Descending
)
# drop the last row(s) after sort, this will have become the shifted row totals, which we don't need re-imported anyway
has_tail = True
while has_tail:
  tail = df.tail(1).iloc[0]
  if bZdUtils.safe_str_to_int(tail['NAME'], tail['NAME']) == bZdUtils.safe_str_to_int(tail['NAME']):
    df = df.iloc[:-1]
  else:
    has_tail = False

raw_data_sheet = "blendus synced raw"

#sys.exit(df)
# 1. Clean up previous test runs
# Try to find the sheet and delete it so we start fresh
try:
    old_test_sheet = sh.worksheet_by_title(raw_data_sheet)
    sh.del_worksheet(old_test_sheet)
    print(f"\nDeleted old raw data sheet '{raw_data_sheet}'.")
except pygsheets.WorksheetNotFound:
    pass # It didn't exist, so nothing to delete

# 2. Create the new test sheet
# We can specify the size, or just let it default
xwks = sh.add_worksheet(raw_data_sheet, rows=100, cols=26)

print(f"Created fresh raw data sheet: {raw_data_sheet}\n")

# Efficient Write clears the sheet and dumps the new data in a SINGLE API call.
# 'start' specifies the top-left cell.
# 'fit' resizes the sheet to match the dataframe dimensions (removes extra empty rows).
xwks.clear() # Wipes everything
xwks.set_dataframe(df, start='A1', copy_head=True, fit=True)

print(f"Successfully updated {len(df)} rows in a single batch.")




print("\n\n", 'SYNC COMPLETE!')

# TOTALS ROW REF    
# { 'NAME': 1865,
#   'Image Folder?': 1390,
#   'blendus?': 54,
#   'whaddayado': '',
#   'aka/alias/group': '',
#   'known as/for': '',
#   'origin': '',
#   'born': 2,
#   'hbd': '',
#   'died': '',
#   'age': 41,
#   'irl': 34,
#   'insta': 64,
#   'youtube': 1,
#   'imdb': 69,
#   'url': 2
# }

# IMAGE/STATS COUNT COLUMNS
# 12 img
# 13 gif
# 14 jpg
# 15 png
# 16 webp
# 17 avif
# 18 subs


