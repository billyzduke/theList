import pandas as pd
import pygsheets
import numpy as np
import json
import os
import re
#import sys
import bZdUtils
from natsort import natsorted

# Auth and Open 
gc = pygsheets.authorize(service_file='credentials.json')
sh = gc.open('@inhumantouch')
wks = sh.worksheet_by_title('blendus synced pretty')

# Efficient Read
# This reads the whole sheet into a pandas dataframe in one go. 
# 'has_header=True' uses the first row as column names.
df = wks.get_as_df(has_header=True)
df = df.dropna(subset=['NAME'])

dicTotals = df.iloc[0]
rem_ladies = df.iloc[1:]

print("\n\n", 'READING THE ROOM!', "\n\n")
print("\n", dicTotals, "\n")
print(f"inhumantouch blendus gsheet contains {len(rem_ladies)} ladies\n")

#moa = Moana, the local drive where all the images of the ladies live
moa_ladies = {}
ladiesPath = '/Volumes/Moana/Images/Ladies/'

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
          moa_ladies[name] = {'img': 0, 'gif': 0, 'jpg': 0, 'jpeg': 0, 'png': 0, 'psd': [], 'psb': [], 'avif': 0, 'webp': 0, 'subs': subs}
          
          # annoying but apparently necessary, even though I cannot even see these where they are supposedly showing up
          imgs = bZdUtils.remove_value_from_list(imgs, '.DS_Store')
            
          # count and sort image files by ext/type 
          for i in imgs:
            moa_ladies[name]['img'] += 1
            
            isGif = re.compile(r'\.gif$')
            m = isGif.search(i)
            if m:
              moa_ladies[name]['gif'] += 1

            isJpg = re.compile(r'\.jpg$')
            m = isJpg.search(i)
            if m:
              moa_ladies[name]['jpg'] += 1

            isJpeg = re.compile(r'\.jpeg$')
            m = isJpeg.search(i)
            if m:
              moa_ladies[name]['jpg'] += 1
              moa_ladies[name]['jpeg'] += 1
            
            isPng = re.compile(r'\.png$')
            m = isPng.search(i)
            if m:
              moa_ladies[name]['png'] += 1
              
            isPsd = re.compile(r'\.psd$')
            m = isPsd.search(i)
            if m:
              moa_ladies[name]['img'] -= 1
              moa_ladies[name]['psd'].append(i)

            isPsb = re.compile(r'\.psb$')
            m = isPsb.search(i)
            if m:
              moa_ladies[name]['img'] -= 1
              moa_ladies[name]['psb'].append(i)

            isAvif = re.compile(r'\.avif$')
            m = isAvif.search(i)
            if m:
              moa_ladies[name]['avif'] += 1

            isWebp = re.compile(r'\.webp$')
            m = isWebp.search(i)
            if m:
              moa_ladies[name]['webp'] += 1
      
loc_ladies = dict(natsorted(moa_ladies.items(), key=lambda x: x[0].casefold()))
# print(loc_ladies)

print(f"\nlocal Ladies image directory contains {len(loc_ladies)} ladies\n")

# first, update the gsheet with local changes
print("\n\n", 'CHECKING gsheet AGAINST local Ladies directory...', "\n")

REMOTE_LADIES_CHANGED = {'REMOTE LADIES ADDED': {}, 'REMOTE LADIES UPDATED': {}}
LOCAL_LADIES_CHANGED = {'LOCAL LADIES ADDED': {}, 'LOCAL LADIES DELETED': {}}

# loop thru local ladies
for name, loc_lady in loc_ladies.items():
  loc_subs = len(loc_lady['subs'])
  named = df['NAME'] == name
  
  # is lady in remote records?
  rem_lady = df.loc[named]
  # if remote record does not already exist, add new row to the gsheet
  if rem_lady.empty:
    new_rem_lady = pd.DataFrame([{'NAME': name, 'Image Folder?': 'Y', 'blendus?': 'N', 'whaddayado': '', 'known as/for': '', 'origin': '', 'born': '', 'hbd': '', 'died': '', 'age': '', 'irl': 'N', 'img': loc_lady['img'], 'gif': loc_lady['img'], 'jpg': loc_lady['jpg'], 'png': loc_lady['png'], 'webp': loc_lady['webp'], 'avif': loc_lady['avif'], 'subs': bZdUtils.safe_str_to_int(loc_subs), 'insta': '', 'youtube': '', 'imdb': '', 'listal': '', 'wikipedia': '', 'url': '', 'blended with…': ''}])
    df = pd.concat([df, new_rem_lady], ignore_index=True)
    # verify addition of new remote lady to dataframe
    named = df['NAME'] == name
    rem_lady = df.loc[named].iloc[0]
    REMOTE_LADIES_CHANGED['REMOTE LADIES ADDED'][name] = rem_lady['NAME']
  else:
    rem_lady = rem_lady.iloc[0]
    
  # print('REMOTE:', name, rem_lady)
  # print('LOCAL:', name, lady, "\n") # copy and paste name from here if mismatch due to special characters

  if rem_lady['Image Folder?'] == 'Y':
    if len(loc_lady['psd']):
      maxBlendus = 0
      for psd in loc_lady['psd']:
        isBlendus = re.compile(r'^blendus-')
        m = isBlendus.search(psd)
        if m:
          blenDims = re.compile(r'[\d]{3,4}')
          m = blenDims.search(psd)
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
    
    cols = ['img', 'gif', 'jpg', 'png', 'webp', 'avif']
    
    # for col in cols:
    #   df.loc[named, col] = int(rem_lady[col]) if rem_lady[col] else 0
    
    imgs = 0
    for col in cols:
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

print(json.dumps(REMOTE_LADIES_CHANGED, indent=2, default=str))

print("\n", 'FLIPPING THE SCRIPT!', "\n", 'CHECKING local Ladies directory AGAINST gsheet...', "\n")

for i, rem_lady in rem_ladies.iterrows():

  if rem_lady['Image Folder?'] == 'Y' and name not in loc_ladies:
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

print(json.dumps(LOCAL_LADIES_CHANGED, indent=2, default=str))

# Handling NaNs
# Google Sheets API throws errors if you try to upload NaN/Infinity. 
# You MUST replace them with empty strings or zeros.
df = df.fillna('') 

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


