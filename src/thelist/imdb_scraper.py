import pygsheets
import pandas as pd
import time
import re
import csv
import os
import urllib.parse
from datetime import datetime

# --- SELENIUM IMPORTS (SAFARI) ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
OUTPUT_DIR = "../../data"
CSV_FILENAME = "imdb_audit.csv"
CSV_OUTPUT_FILE = os.path.join(OUTPUT_DIR, CSV_FILENAME)

# Only count rows where we actually perform a search
REMOTE_QUERY_LIMIT = 25 
# How many horizontal results to support (Res1...ResN)
MAX_RESULTS_COLUMNS = 15

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
    return webdriver.Safari()

# 2. HELPER: PARSE DATE
def parse_imdb_date(date_str):
    if not date_str: return ""
    date_str = date_str.strip()
    try:
        dt = datetime.strptime(date_str, "%B %d, %Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', date_str)
    if year_match: return year_match.group(1)
    return date_str

# 3. HELPER: DIRECT IMDB SEARCH (STRICT MATCHING)
def search_imdb_direct(driver, target_name):
    encoded_name = urllib.parse.quote(target_name)
    url = SEARCH_URL_BASE.format(encoded_name)
    
    found_ids = []
    
    try:
        driver.get(url)
        
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "ipc-metadata-list"))
            )
        except:
            return []

        results_section = driver.find_element(By.CLASS_NAME, "ipc-metadata-list")
        # Find all result items
        items = results_section.find_elements(By.CLASS_NAME, "ipc-metadata-list-summary-item")
        
        target_clean = target_name.strip().lower()

        for item in items:
            try:
                link_el = item.find_element(By.CLASS_NAME, "ipc-metadata-list-summary-item__t")
                text_raw = link_el.text.strip()
                href = link_el.get_attribute("href")

                # CLEAN THE RESULT NAME
                # Removes IMDb numbering like " (I)", " (II)", " (12)"
                text_clean = re.sub(r'\s*\([IVX0-9]+\)$', '', text_raw).strip().lower()

                # STRICT MATCH CHECK
                if text_clean != target_clean:
                    # If we hit a non-match, we stop searching entirely
                    break

                if href and "/name/nm" in href:
                    match = re.search(r'/name/(nm\d+)', href)
                    if match:
                        found_ids.append(match.group(1))
                        
                        # Stop if we hit our column max
                        if len(found_ids) >= MAX_RESULTS_COLUMNS:
                            break
            except:
                continue
                
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

    except Exception:
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

# Generate Headers dynamically based on Max Columns
fieldnames = ["NAME", "STATUS"]
for i in range(1, MAX_RESULTS_COLUMNS + 1):
    fieldnames.extend([f"Res{i}_Name", f"Res{i}_ID", f"Res{i}_Born"])

print(f"Starting Direct IMDb Scan (Safari). Limit: {REMOTE_QUERY_LIMIT} new queries.")
print(f"Output: {CSV_OUTPUT_FILE}")

# Initialize counters
processed_queries = 0
driver = None

try:
    with open(CSV_OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        
        for index, row in df.iterrows():
            # CHECK LIMIT: Stop only if we've hit the limit of NEW queries
            if processed_queries >= REMOTE_QUERY_LIMIT:
                print(f"\nLimit of {REMOTE_QUERY_LIMIT} remote queries reached. Stopping.")
                break

            original_name = str(row['NAME'])
            existing_imdb = str(row.get('imdb', '')).strip()

            # Initialize row dict with empty strings for all potential columns
            row_data = {field: "" for field in fieldnames}
            row_data["NAME"] = original_name

            # --- CASE 1: ALREADY EXISTS ---
            if existing_imdb:
                row_data["STATUS"] = "PASSED (EXISTING)"
                writer.writerow(row_data)
                csv_file.flush()
                # Do NOT increment processed_queries
                continue

            # --- CASE 2: NEW SEARCH ---
            # Initialize driver only when we actually need to search
            if driver is None:
                driver = init_driver()

            processed_queries += 1
            print(f"[{processed_queries}/{REMOTE_QUERY_LIMIT}] Searching: {original_name}...", end="\r")
            
            # 1. Direct Search (Strict)
            nm_ids = search_imdb_direct(driver, original_name)
            
            if not nm_ids:
                row_data["STATUS"] = "NO_RESULTS"
            else:
                row_data["STATUS"] = f"FOUND_{len(nm_ids)}"
                
                # 2. Visit Profiles for all matches found
                for i, nm_id in enumerate(nm_ids):
                    res_num = i + 1
                    p_name, p_born = scrape_imdb_profile(driver, nm_id)
                    
                    row_data[f"Res{res_num}_Name"] = p_name
                    row_data[f"Res{res_num}_ID"] = nm_id
                    row_data[f"Res{res_num}_Born"] = p_born
                    
                    time.sleep(0.5) # Slight throttle between profile loads

            writer.writerow(row_data)
            csv_file.flush()
            
            # Pause between searches
            time.sleep(1.0)

finally:
    if driver:
        print("\nClosing Browser...")
        driver.quit()
    print(f"Done. Results saved to {CSV_OUTPUT_FILE}")