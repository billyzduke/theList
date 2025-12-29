#from charset_normalizer import detect
import os
import re
import gspread
from natsort import natsorted
#from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.service_account import Credentials


# Define the scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
SERVICE_ACCOUNT_FILE = 'credentials.json'

# Authenticate with credentials
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, SCOPES)
client = gspread.authorize(creds)

# Open the Google Sheet
sheet = client.open('@inhumantouch').get_worksheet(1)

# TEST Fetch the first row of data
# first_row = sheet.row_values(1)
# print(f"First row of data: {first_row}")

dicList = sheet.get_all_values()

'''

NAME              2073
Image Folder?     1431
blendus?            67
whaddayado
known as/for
origin
born                 2
hbd
died                36
age                 41
irl                 36
img              19271
gif                  6
jpg              14948
png                918
webp              3399
avif                 0
subs                 1
insta               92
youtube              4
imdb               205
listal              64
wikipedia           18
bandcamp             1
spotify              1
url                 17
blended with…
Name: 0, dtype: object
NAME                    Ann Wilson
Image Folder?            Y (combo)
blendus?                         N
whaddayado       Musician / Singer
known as/for                 Heart
origin                    American
born                    1950-06-19
hbd                          FALSE
died
age                             75
irl                              N
img                             10
gif                              0
jpg                             10
png                              0
webp                             0
avif                             0
subs                             0
insta
youtube
imdb
listal
wikipedia
bandcamp
spotify
url
blended with…
Name: 1, dtype: object

'''