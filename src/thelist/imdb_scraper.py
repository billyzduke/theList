import pygsheets
import pandas as pd
import time
import re
import csv
import os
import urllib.parse
from datetime import datetime

# --- SELENIUM IMPORTS ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
OUTPUT_DIR = "../../data"
CSV_FILENAME = "imdb_audit.csv"  # Reverted filename
CSV_OUTPUT_FILE = os.path.join(OUTPUT_DIR, CSV_FILENAME)

# Constraints
REMOTE_QUERY_LIMIT = 25  # Stops after this many *new* rows are processed
MAX_RESULTS = 15         # Max results per name type (Short vs Full)
SEARCH_URL_BASE = "https://www.imdb.com/find/?q={}&s=nm"

# SKIP LOGIC
# Set to "" to start from the beginning.
# Set to a specific name (e.g., "Nina Gordon") to skip everything before it.
START_FROM_NAME = "Alithea Tuttle" 

# --- ENSURE DIRECTORY EXISTS ---
if not os.path.exists(OUTPUT_DIR):
  try:
    os.makedirs(OUTPUT_DIR)
  except OSError:
    pass

# 1. SETUP SAFARI DRIVER
def init_driver():
  print("Initializing Safari Browser...")
  return webdriver.Safari()

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

# 3. HELPER: SELECTOR UPDATE (BASED ON HTML SNIPPET)
def search_and_scrape(driver, search_name, max_results=MAX_RESULTS):
  if not search_name or not isinstance(search_name, str):
    return []
    
  encoded_name = urllib.parse.quote(search_name)
  url = SEARCH_URL_BASE.format(encoded_name)
  results_data = []
  
  target_clean = " ".join(search_name.strip().lower().split())
  print(f"\n--- DEBUG: Searching for '{search_name}' ---")
  
  try:
    driver.get(url)
    try:
      # Wait for the generic list container
      WebDriverWait(driver, 3).until(
        EC.presence_of_element_located((By.CLASS_NAME, "ipc-metadata-list"))
      )
    except:
      print("    [!] No results container found.")
      return [] 

    # STRATEGY: Find the specific link wrapper class you identified
    # This targets <a class="ipc-title-link-wrapper" href="/name/...">
    link_items = driver.find_elements(By.CSS_SELECTOR, "a.ipc-title-link-wrapper[href*='/name/']")
    
    print(f"    [i] Found {len(link_items)} potential name links.")

    valid_ids = []
    for index, link_el in enumerate(link_items):
      try:
        # 1. Get Text from the H3 inside the link
        try:
            title_el = link_el.find_element(By.CLASS_NAME, "ipc-title__text")
            # Force JS extraction to be safe
            text_raw = driver.execute_script("return arguments[0].textContent;", title_el).strip()
        except:
            # Fallback if h3 is missing
            text_raw = driver.execute_script("return arguments[0].textContent;", link_el).strip()

        # 2. Clean & Normalize
        text_normalized = text_raw.replace('\xa0', ' ').replace('\u200b', '')
        text_clean = re.sub(r'\s*\(.*?\)$', '', text_normalized).strip().lower()
        text_clean = " ".join(text_clean.split())
        
        print(f"    Item {index+1}: Raw='{text_raw}' | Cleaned='{text_clean}'")

        # 3. Compare
        if text_clean != target_clean:
          print(f"       [x] MISMATCH (Expected '{target_clean}')")
          continue
        else:
          print("       [✓] MATCH!")

        href = link_el.get_attribute("href")
        match = re.search(r'/name/(nm\d+)', href)
        if match:
          valid_ids.append(match.group(1))
          if len(valid_ids) >= max_results:
            break
            
      except Exception as e:
        print(f"    [!] Error processing item {index}: {e}")
        continue
    
    # Phase 2: Visit Profiles
    for nm_id in valid_ids:
      try:
        driver.get(f"https://www.imdb.com/name/{nm_id}/")
        born = ""
        try:
          birth_div = driver.find_element(By.CSS_SELECTOR, "[data-testid='birth-and-death-birthdate']")
          raw_born = driver.execute_script("return arguments[0].textContent;", birth_div)
          born = parse_imdb_date(raw_born.replace("Born", "").strip())
        except:
          born = ""
        results_data.append({'id': nm_id, 'born': born})
        time.sleep(0.5) 
      except:
        results_data.append({'id': nm_id, 'born': "Error"})
        
    return results_data

  except Exception as e:
    print(f" [Fatal Error: {e}] ", end="")
    return []

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

# Generate Dynamic Fieldnames
fieldnames = ["NAME", "STATUS"]
for prefix in ["Short", "Full"]:
  for i in range(1, MAX_RESULTS + 1):
    fieldnames.extend([f"{prefix}_Res{i}_ID", f"{prefix}_Res{i}_Born"])

print(f"Starting Scan. Limit: {REMOTE_QUERY_LIMIT} new rows.")
if START_FROM_NAME:
  print(f"Skipping until name: '{START_FROM_NAME}'")
print(f"Output: {CSV_OUTPUT_FILE}")

processed_count = 0
driver = None
start_found = False 

# If no start name is set, we start strictly from the beginning
if not START_FROM_NAME:
  start_found = True

try:
  with open(CSV_OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    
    for index, row in df.iterrows():
      
      short_name = str(row['NAME']).strip()
      
      # --- START LOGIC ---
      if not start_found:
        if short_name.lower() == START_FROM_NAME.lower():
          start_found = True
          print(f"Found start target: {short_name}. Beginning processing...")
        else:
          continue

      # --- LIMIT CHECK ---
      if processed_count >= REMOTE_QUERY_LIMIT:
        print(f"\nLimit of {REMOTE_QUERY_LIMIT} queries reached. Stopping.")
        break

      full_name = str(row.get('Full Name', '')).strip() 
      existing_imdb = str(row.get('imdb', '')).strip()

      # --- SKIP EXISTING ---
      if existing_imdb:
        continue

      # --- BEGIN NEW SEARCH ---
      if driver is None:
        driver = init_driver()

      processed_count += 1
      print(f"[{processed_count}/{REMOTE_QUERY_LIMIT}] Processing: {short_name}...", end="\r")

      row_data = {field: "" for field in fieldnames}
      row_data["NAME"] = short_name

      # 1. Search Short Name
      short_results = search_and_scrape(driver, short_name)
      for i, res in enumerate(short_results):
        row_data[f"Short_Res{i+1}_ID"] = res['id']
        row_data[f"Short_Res{i+1}_Born"] = res['born']

      # 2. Search Full Name (Only if different)
      if full_name and full_name.lower() != short_name.lower():
        full_results = search_and_scrape(driver, full_name)
        for i, res in enumerate(full_results):
          row_data[f"Full_Res{i+1}_ID"] = res['id']
          row_data[f"Full_Res{i+1}_Born"] = res['born']

      # Status Update
      found_short = len(short_results)
      found_full = sum(1 for k,v in row_data.items() if k.startswith("Full_Res") and v) // 2
      row_data["STATUS"] = f"FOUND_S({found_short})_F({found_full})"

      writer.writerow(row_data)
      csv_file.flush()
      
      # Pause between rows
      time.sleep(1.0)

finally:
  if driver:
    print("\nClosing Browser...")
    driver.quit()
  print(f"\nDone. Results saved to {CSV_OUTPUT_FILE}")