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

print('Check gsheet against local directory:')

blendums = {}

for name, lady in loc_ladies.items():
  # print(name) # copy and paste from here if mismatch due to special characters
  if name in rem_ladies:
    rem = rem_ladies[name]
    # print('REMOTE:', name, rem)
    # print('LOCAL:', name, lady)
    if rem_ladies[name]['Image Folder?'] == 'Y':
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
          blendums[name] = {'blendus?': rem['blendus?'], 'maxBlendus': maxBlendus}
          cell = sheet.findall(name).pop(0)
          if maxBlendus <= 1280:
            if maxBlendus not in [900, 1024, 1280]:
              maxBlendus = 'rando'
          else:
            maxBlendus = 'xlarge'
          sheet.update_cell(cell.row, cell.col + 2, maxBlendus)
    
      rem['img'] = int(rem['img']) if rem['img'] else 0
      rem['gif'] = int(rem['gif']) if rem['gif'] else 0
      rem['jpg'] = int(rem['jpg']) if rem['jpg'] else 0
      rem['png'] = int(rem['png']) if rem['png'] else 0
      rem['webp'] = int(rem['webp']) if rem['webp'] else 0
      rem['avif'] = int(rem['avif']) if rem['avif'] else 0
      rem['subs'] = int(rem['subs']) if rem['subs'] else 0
      
      lady_subs = len(lady['subs'])
      
      if rem['img'] != lady['img'] or rem['gif'] != lady['gif'] or rem['jpg'] != lady['jpg'] or rem['png'] != lady['png'] or rem['webp'] != lady['webp'] or rem['avif'] != lady['avif'] or rem['subs'] != lady_subs:
        if cell == 0:
          cell = sheet.findall(name).pop(0)
        
      # if rem['img'] != lady['img']:
      #   sheet.update_cell(cell.row, cell.col + 11, lady['img'])
      if rem['gif'] != lady['gif']:
        sheet.update_cell(cell.row, cell.col + 12, lady['gif'])
      if rem['jpg'] != lady['jpg']:
        sheet.update_cell(cell.row, cell.col + 13, lady['jpg'])
      if rem['png'] != lady['png']:
        sheet.update_cell(cell.row, cell.col + 14, lady['png'])
      if rem['webp'] != lady['webp']:
        sheet.update_cell(cell.row, cell.col + 15, lady['webp'])
      if rem['avif'] != lady['avif']:
        sheet.update_cell(cell.row, cell.col + 16, lady['avif'])
      if rem['subs'] != lady_subs:
        sheet.update_cell(cell.row, cell.col + 17, lady_subs)
      # if lady['jpeg'] > 0:
      # if (len(lady['psd']) or len(lady['psb'])):
    print()
  else:  
    sheet.update_cell(next_empty_row, 1, name) # NAME
    sheet.update_cell(next_empty_row, 2, 'Y') # Image Folder?
    sheet.update_cell(next_empty_row, 3, 'N')
    next_empty_row += 1

print('Check local directory against gsheet:')

for name, lady in rem_ladies.items():
  if lady['Image Folder?'] == 'Y' and name not in loc_ladies:
    print(name)

print(blendums)

    
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

# 12 img
# 13 gif
# 14 jpg
# 15 png
# 16 webp
# 17 avif
# 18 subs
