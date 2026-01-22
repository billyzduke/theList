import pygsheets
import pandas as pd
import time
import re
import csv
import os
import sys
import urllib.parse
from datetime import datetime

# --- SELENIUM IMPORTS (SAFARI) ---
from selenium import webdriver
from selenium.webdriver.safari.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
OUTPUT_DIR = "../../data"
CSV_FILENAME = "imdb_audit.csv"
CSV_OUTPUT_FILE = os.path.join(OUTPUT_DIR, CSV_FILENAME)

ROW_LIMIT = 25 # 500
SEARCH_URL_BASE = "https://www.imdb.com/find/?q={}&s=nm"

# --- ENSURE DIRECTORY EXISTS ---
if not os.path.exists(OUTPUT_DIR):
  try:
    os.makedirs(OUTPUT_DIR)
  except OSError:
    pass

# 1. SETUP SAFARI DRIVER
def init_driver():
  print("Initializing Safari Browser...")
  # Safari driver is built-in on macOS. No separate download needed.
  # Ensure "Allow Remote Automation" is enabled in Safari > Develop menu.
  driver = webdriver.Safari()
  return driver

# 2. HELPER: PARSE DATE
def parse_imdb_date(date_str):
  if not date_str:
    return ""
  date_str = date_str.strip()
  try:
    dt = datetime.strptime(date_str, "%B %d, %Y")
    return dt.strftime("%Y-%m-%d")
  except ValueError:
    pass
  year_match = re.search(r'\b(19\d{2}|20\d{2})\b', date_str)
  if year_match:
    return year_match.group(1)
  return date_str

# 3. HELPER: DIRECT IMDB SEARCH
def search_imdb_direct(driver, name):
  encoded_name = urllib.parse.quote(name)
  url = SEARCH_URL_BASE.format(encoded_name)
  
  try:
    driver.get(url)
    
    # Wait for results
    try:
      WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CLASS_NAME, "ipc-metadata-list"))
      )
    except:
      return []

    results_section = driver.find_element(By.CLASS_NAME, "ipc-metadata-list")
    links = results_section.find_elements(By.TAG_NAME, "a")
    
    found_ids = []
    seen = set()
    
    for link in links:
      href = link.get_attribute("href")
      if href and "/name/nm" in href:
        match = re.search(r'/name/(nm\d+)', href)
        if match:
          nm_id = match.group(1)
          if nm_id not in seen:
            seen.add(nm_id)
            found_ids.append(nm_id)
            if len(found_ids) >= 3:
              break
              
    return found_ids

  except Exception as e:
    print(f" [Search Error: {e}] ", end="")
    return []

# 4. HELPER: SCRAPE IMDB PROFILE
def scrape_imdb_profile(driver, nm_id):
  url = f"https://www.imdb.com/name/{nm_id}/"
  try:
    driver.get(url)
    
    # Extract Name
    try:
      name_tag = WebDriverWait(driver, 3).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='hero__primary-text']"))
      )
      name = name_tag.text.strip()
    except:
      name = "Unknown/Error"

    # Extract Birthdate
    born = ""
    try:
      birth_div = driver.find_element(By.CSS_SELECTOR, "[data-testid='birth-and-death-birthdate']")
      raw_text = birth_div.text
      clean_text = raw_text.replace("Born", "").strip()
      born = parse_imdb_date(clean_text)
    except:
      born = "" 

    return name, born

  except Exception as e:
    return "Error", ""

# ==========================================
# MAIN EXECUTION
# ==========================================

print("Connecting to Google Sheets...")
gc = pygsheets.authorize(service_file='credentials.json')
sh = gc.open('@inhumantouch')
wks = sh.worksheet_by_title('blendus synced raw')

print("Fetching source data...")
df = wks.get_as_df(has_header=True)
df = df.dropna(subset=['NAME'])

if len(df) > ROW_LIMIT:
  print(f"Limiting execution to first {ROW_LIMIT} rows.")
  df = df.head(ROW_LIMIT)

# START BROWSER (SAFARI)
driver = init_driver()

fieldnames = [
  "NAME", "STATUS",
  "Res1_Name", "Res1_ID", "Res1_Born",
  "Res2_Name", "Res2_ID", "Res2_Born",
  "Res3_Name", "Res3_ID", "Res3_Born"
]

print(f"Starting Direct IMDb Scan (Safari). Output: {CSV_OUTPUT_FILE}")

try:
  with open(CSV_OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    
    for index, row in df.iterrows():
      original_name = str(row['NAME'])
      existing_imdb = str(row.get('imdb', '')).strip()

      row_data = {
        "NAME": original_name,
        "STATUS": "",
        "Res1_Name": "", "Res1_ID": "", "Res1_Born": "",
        "Res2_Name": "", "Res2_ID": "", "Res2_Born": "",
        "Res3_Name": "", "Res3_ID": "", "Res3_Born": ""
      }

      if existing_imdb:
        row_data["STATUS"] = "PASSED (EXISTING)"
        writer.writerow(row_data)
        csv_file.flush()
        continue

      print(f"[{index}] Searching: {original_name}...", end="\r")
      
      # 1. Direct Search
      nm_ids = search_imdb_direct(driver, original_name)
      
      if not nm_ids:
        row_data["STATUS"] = "NO_RESULTS"
      else:
        row_data["STATUS"] = f"FOUND_{len(nm_ids)}"
        
        # 2. Visit Profiles
        for i, nm_id in enumerate(nm_ids):
          res_num = i + 1
          p_name, p_born = scrape_imdb_profile(driver, nm_id)
          
          row_data[f"Res{res_num}_Name"] = p_name
          row_data[f"Res{res_num}_ID"] = nm_id
          row_data[f"Res{res_num}_Born"] = p_born
          
          time.sleep(1)

      writer.writerow(row_data)
      csv_file.flush()
      
      # Pause between rows
      time.sleep(1.5)

finally:
  print("\nClosing Browser...")
  driver.quit()
  print(f"Done. Results saved to {CSV_OUTPUT_FILE}")