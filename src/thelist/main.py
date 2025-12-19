from charset_normalizer import detect
import os
import re
import gspread
import bZdUtils
from natsort import natsorted
from oauth2client.service_account import ServiceAccountCredentials


# Define the scope
scope = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Authenticate with credentials
credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(credentials)

# Open the Google Sheet
sheet = client.open('@inhumantouch').get_worksheet(1)

# inhale all rows and column values
dicLess = sheet.get_all_values()

# column labels
dicKeys = dicLess.pop(0)
#print(dicKeys)

# column totals
dicTots = dicLess.pop(0)
dicTotals = dict(zip(dicKeys, dicTots))

#gsh = google sheet
gsh_ladies = {}

# gather/organize/label the rows from the google sheet
for row in dicLess:
  dicVals = row
  dicList = dict(zip(dicKeys, dicVals))
  
  if len(dicList['NAME']) > 0:
    gsh_ladies[dicList.pop('NAME')] = dicList
    #print(dicList)

rem_ladies = dict(natsorted(gsh_ladies.items(), key=lambda x: x[0].casefold()))
# print(rem_ladies.keys())

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
          print('LOCAL COMBO FOLDER DETECTED (AND BYPASSED):', name, "\n")
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

next_empty_row = len(rem_ladies) + 3
# print(listRefs)

# first, update the gsheet with local changes
print("\n\n", 'READING THE ROOM!', "\n\n")
print(f"inhumantouch blendus gsheet contains {len(rem_ladies)} ladies\n")
print("\n", dicTotals, "\n")
print(f"local Ladies image directory contains {len(loc_ladies)} ladies\n")
print("\n\n", 'CHECKING gsheet AGAINST local Ladies directory...', "\n")

# loop thru local ladies
for name, lady in loc_ladies.items():
  loc_subs = len(lady['subs'])
  
  # if local lady folder has images or subdirectories, add it to the gsheet
  if name not in rem_ladies and (lady['img'] > 0 or loc_subs > 0):
    sheet.update_cell(next_empty_row, 1, name) # NAME
    sheet.update_cell(next_empty_row, 2, 'Y') # Image Folder?
    sheet.update_cell(next_empty_row, 3, 'N')
    rem_ladies[name] = {'Image Folder?': 'Y', 'blendus?': 'N', 'whaddayado': '', 'known as/for': '', 'origin': '', 'born': '', 'hbd': '', 'died': '', 'age': '', 'irl': 'N', 'img': lady['img'], 'gif': lady['img'], 'jpg': lady['jpg'], 'png': lady['png'], 'webp': lady['webp'], 'avif': lady['avif'], 'subs': bZdUtils.safe_str_to_int(loc_subs), 'insta': '', 'youtube': '', 'imdb': '', 'listal': '', 'wikipedia': '', 'url': '', 'blended with…': ''}
    print('REMOTE LADY ADDED:', name, rem_ladies[name], "\n")
    next_empty_row += 1
    
  rem = rem_ladies[name]
  # print('REMOTE:', name, rem)
  # print('LOCAL:', name, lady, "\n") # copy and paste name from here if mismatch due to special characters

  if rem['Image Folder?'] == 'Y':
    cell = 0
  # == 'N':
    # cell = sheet.findall(name).pop(0)
    # sheet.update_cell(cell.row, cell.col + 1, 'Y')
  # else:
    if len(lady['psd']):
      maxBlendus = 0
      for psd in lady['psd']:
        isBlendus = re.compile(r'^blendus-')
        m = isBlendus.search(psd)
        if m:
          blenDims = re.compile(r'[\d]{3,4}')
          m = blenDims.search(psd)
          blendus = int(m.group())
          if blendus > maxBlendus:
            maxBlendus = blendus
      if maxBlendus > 0 and rem['blendus?'] != str(maxBlendus):
        if maxBlendus <= 1280:
          if maxBlendus not in [900, 1024, 1280]:
            maxBlendus = 'rando'
        else:
          maxBlendus = 'xlarge'
        if rem['blendus?'] != str(maxBlendus):
          cell = sheet.findall(name).pop(0)
          #bZdUtils.line_info()
          sheet.update_cell(cell.row, cell.col + 2, maxBlendus)
          print('REMOTE LADY UPDATED:', name, {'blendus?': maxBlendus}, "\n")
          
    cols = ['img', 'gif', 'jpg', 'png', 'webp', 'avif']
          
    for col in cols:
      rem[col] = int(rem[col]) if rem[col] else 0
        
    for col in cols:
      if col != 'img':
        if cell == 0 and (bZdUtils.safe_str_to_int(rem['subs']) != loc_subs or rem[col] != lady[col]):
          #print(name, "- rem['subs']:", rem['subs'], type(rem['subs']), type(bZdUtils.safe_str_to_int(rem['subs'])), "- loc_subs:", loc_subs, type(loc_subs))
          #print(name, "- cell:", cell, type(cell), "- rem[col]:", rem[col], type(rem[col]), "- lady[col]:", lady[col], type(lady[col]))
          #print("rem:", rem)
          #print("lady:", lady)
          cell = sheet.findall(name).pop(0)
          bZdUtils.line_info()
          
    col_shift = 12
    imgs = 0
    
    for col in cols:
      if col != 'img':
        imgs += lady[col]
        if rem[col] != lady[col]:
          sheet.update_cell(cell.row, cell.col + col_shift, lady[col])
          print('REMOTE LADY UPDATED:', name, {col: lady[col]}, "\n")
        col_shift += 1
      
    if imgs == 0 and loc_subs == 0:
      if cell == 0:
        cell = sheet.findall(name).pop(0)
        #bZdUtils.line_info()
      sheet.update_cell(cell.row, 2, 'N') # Image Folder?
      print('REMOTE LADY UPDATED:', name, {'Image Folder?': 'N'}, "\n")
      
      try:
        ladyPath = ladiesPath + name
        os.rmdir(ladyPath)
        print('EMPTY LOCAL FOLDER DELETED:', ladyPath, "\n")
      except OSError as e:
        print('ERROR ATTEMPTING TO DELETE LOCAL FOLDER:', ladyPath, "\n", e, "\n")
      
    if bZdUtils.safe_str_to_int(rem['subs']) != loc_subs:
      sheet.update_cell(cell.row, cell.col + 17, loc_subs)
      print('REMOTE LADY UPDATED:', name, {'subs': loc_subs}, "\n")

print("\n", 'FLIPPING THE SCRIPT!', "\n", 'CHECKING local Ladies directory AGAINST gsheet...', "\n")

for name, lady in rem_ladies.items():
  if lady['Image Folder?'] == 'Y' and name not in loc_ladies:
    ladyPath = ladiesPath + name
    try:
      os.mkdir(ladyPath) # Creates a single directory
      print('LOCAL FOLDER ADDED:', ladyPath, "\n")
    except FileExistsError:
      print('LOCAL FOLDER ALREADY EXISTS:', ladyPath, "\n")
    except PermissionError:
      print('PERMISSION DENIED WHILE ATTEMPTING TO CREATE LOCAL FOLDER:', ladyPath, "\n")
    except Exception as e:
      print('ERROR ATTEMPTING TO CREATE LOCAL FOLDER:', name, "\n", e, "\n")

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
