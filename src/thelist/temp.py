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