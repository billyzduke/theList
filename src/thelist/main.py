from charset_normalizer import detect
import os
import re
import gspread
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

# TEST Fetch the first row of data
# first_row = sheet.row_values(1)
# print(f"First row of data: {first_row}")

dicList = sheet.get_all_records()

listRefs = dicList.pop(0)
# print(listRefs)

gsh_ladies = {}
for row in dicList:
  if len(row['NAME']) > 0:
    gsh_ladies[row.pop('NAME')] = row
    # print(row)
  
rem_ladies = dict(natsorted(gsh_ladies.items(), key=lambda x: x[0].casefold()))
# print(rem_ladies.keys())

moa_ladies = {}
ladiesPath = '/Volumes/Moana/Images/Ladies/'

for root, subs, imgs in os.walk(ladiesPath):
  if root.count('/') == 5:
    name = os.path.basename(root)
    if len(name):
      notName = re.compile(r'^!')
      m = notName.search(name)
      if not m:
        multiNames = re.compile(r' & ')
        m = multiNames.search(name)
        if not m:
          # name = name.encode().decode('utf-8')    
          moa_ladies[name] = {'img': 0, 'gif': 0, 'jpg': 0, 'jpeg': 0, 'png': 0, 'psd': [], 'psb': [], 'avif': 0, 'webp': 0, 'subs': subs}
          
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

print('CHECKING gsheet AGAINST local Ladies directory...', "\n")

for name, lady in loc_ladies.items():
  loc_subs = len(lady['subs'])
  
  if name not in rem_ladies and (lady['img'] > 0 or loc_subs > 0):
    sheet.update_cell(next_empty_row, 1, name) # NAME
    sheet.update_cell(next_empty_row, 2, 'Y') # Image Folder?
    sheet.update_cell(next_empty_row, 3, 'N')
    rem_ladies[name] = {'Image Folder?': 'Y', 'blendus?': 'N', 'whaddayado': '', 'known as/for': '', 'origin': '', 'born': '', 'hbd': '', 'died': '', 'age': '', 'irl': 'N', 'img': lady['img'], 'gif': lady['img'], 'jpg': lady['jpg'], 'png': lady['png'], 'webp': lady['webp'], 'avif': lady['avif'], 'subs': loc_subs, 'insta': '', 'youtube': '', 'imdb': '', 'listal': '', 'wikipedia': '', 'url': ''}
    print('REMOTE LADY ADDED:', name, rem_ladies[name], "\n")
    next_empty_row += 1
    
  rem = rem_ladies[name]
  if name == 'Brandi Carlile':
    print('REMOTE:', name, rem)
    print('LOCAL:', name, lady, "\n") # copy and paste name from here if mismatch due to special characters

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
      if maxBlendus > 0 and rem['blendus?'] != maxBlendus:
        if maxBlendus <= 1280:
          if maxBlendus not in [900, 1024, 1280]:
            maxBlendus = 'rando'
        else:
          maxBlendus = 'xlarge'
        if rem['blendus?'] != maxBlendus:
          cell = sheet.findall(name).pop(0)
          sheet.update_cell(cell.row, cell.col + 2, maxBlendus)
          print('REMOTE LADY UPDATED:', name, {'blendus?': maxBlendus}, "\n")
          
    cols = ['img', 'gif', 'jpg', 'png', 'webp', 'avif']
          
    for col in cols:
      rem[col] = int(rem[col]) if rem[col] else 0
        
    for col in cols:
      if cell == 0 and (rem['subs'] != loc_subs or rem[col] != lady[col]):
        cell = sheet.findall(name).pop(0)
        
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
      try:
        os.rmdir(root)
        print('EMPTY LOCAL FOLDER DELETED:', name, "\n")
      except OSError as e:
        print('ERROR ATTEMPTING TO DELETE LOCAL FOLDER:', name, "\n", e, "\n")
      
    if rem['subs'] != loc_subs:
      sheet.update_cell(cell.row, cell.col + 17, loc_subs)
      print('REMOTE LADY UPDATED:', name, {'subs': loc_subs}, "\n")

print('CHECKING local Ladies directory AGAINST gsheet...', "\n")

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
