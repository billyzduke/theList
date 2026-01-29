import pygsheets
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os
import re
from util import get_first_pos_arg 
from datetime import datetime
import csv

# --- CONFIGURATION ---
OUTPUT_DIR = "../../data"
CSV_FILENAME = "wiki_audit.csv"
CSV_OUTPUT_FILE = os.path.join(OUTPUT_DIR, CSV_FILENAME)

WIKI_API_URL = "https://en.wikipedia.org/w/api.php"

# SKIP LOGIC
# Set to "" to start from the beginning.
# Set to a specific name (e.g., "Nina Gordon") to skip everything before it.
if __name__ == "__main__":
  # Check if the user actually provided a name
  START_FROM_NAME = get_first_pos_arg()
  if not START_FROM_NAME:
    START_FROM_NAME = ""

# 1. AUTH AND OPEN
print("Connecting to Google Sheets...")
gc = pygsheets.authorize(service_file='credentials.json')
sh = gc.open('@inhumantouch')
wks = sh.worksheet_by_title('blendus synced pretty')

# 2. READ DATA
print("Fetching source data...")
df = wks.get_as_df(has_header=True)

# Clean up empty rows
df = df.dropna(subset=['NAME'])
if not df.empty:
  df = df.drop(df.index[0]) # Drop sub-header

# --- HELPER: DATE PARSER ---
def extract_birth_date(soup):
  """ Tries to find the birth date in YYYY-MM-DD format. """
  bday_tag = soup.find(class_="bday")
  if bday_tag:
    return bday_tag.get_text().strip()

  infobox = soup.find(class_="infobox")
  if infobox:
    for row in infobox.find_all("tr"):
      header = row.find("th")
      if header and "Born" in header.get_text():
        data = row.find("td")
        if data:
          text = data.get_text(" ", strip=True).replace('\xa0', ' ')
          text = re.sub(r'\[.*?\]', '', text)
          
          match_dmy = re.search(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', text)
          if match_dmy:
            try:
              return datetime.strptime(match_dmy.group(0), "%d %B %Y").strftime("%Y-%m-%d")
            except:
              pass

          match_mdy = re.search(r'([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})', text)
          if match_mdy:
            try:
              return datetime.strptime(match_mdy.group(0), "%B %d, %Y").strftime("%Y-%m-%d")
            except:
              pass

          year_match = re.search(r'\b(19\d{2}|20\d{2})\b', text)
          if year_match:
            return year_match.group(1)
  return ""

# --- HELPER: RESOLVE REDIRECTS ---
def get_canonical_slug_from_api(title_or_slug):
  params = {
    "action": "query",
    "format": "json",
    "titles": title_or_slug,
    "redirects": 1 
  }
  try:
    # timeout=30 seconds
    resp = requests.get(WIKI_API_URL, params=params, headers={'User-Agent': 'Bot/1.0'}, timeout=30)
    data = resp.json()
    
    pages = data.get("query", {}).get("pages", {})
    for pid, pdata in pages.items():
      if pid == "-1":
        return title_or_slug.replace(" ", "_")
      final_title = pdata.get("title", "")
      if final_title:
        return final_title.replace(" ", "_")
    return title_or_slug.replace(" ", "_")
  except:
    return title_or_slug.replace(" ", "_")

# --- HELPER: SCRAPER ---
def scrape_wiki_page(slug, original_name):
  session = requests.Session()
  session.headers.update({'User-Agent': 'Bot/1.0 (Researching internal data consistency)'})
  
  url = f"https://en.wikipedia.org/wiki/{slug}"

  try:
    # timeout=30 seconds
    page_resp = session.get(url, timeout=30) 
    if page_resp.status_code != 200:
      return "", "404_NOT_FOUND", ""
      
    soup = BeautifulSoup(page_resp.content, 'html.parser')
    
    if "may refer to:" in soup.get_text()[:500]:
      return "", "DISAMBIGUATION_PAGE", ""

    birth_date = extract_birth_date(soup)

    content_div = soup.find(id="mw-content-text")
    if not content_div:
      return "", "NO_CONTENT", birth_date

    paragraphs = content_div.select("div.mw-parser-output > p")
    target_p = None
    for p in paragraphs:
      text = p.get_text().strip()
      if text and not p.find('span', {'id': 'coordinates'}):
        target_p = p
        break
    
    if not target_p:
      return "", "NO_PARAGRAPH", birth_date

    collected_parts = []
    
    # Iterate through children to maintain order
    for child in target_p.children:
      # Stop at the start of bio details (usually indicated by parenthesis with 'born')
      if isinstance(child, str) and '(' in child:
        break
      if child.name is None and '(' in str(child):
        break

      # 1. BOLD TAGS (The Names)
      if child.name in ['b', 'strong']:
        text = child.get_text().strip()
        if text:
          collected_parts.append(text)
      
      # 2. UNBOLDED TEXT (Look for Nicknames in quotes)
      elif isinstance(child, str) or child.name is None:
        text = str(child)
        # Regex to find text inside quotes (standard or curly)
        quotes = re.findall(r'["“](.*?)["”]', text)
        for q in quotes: 
          if q.strip(): 
            # Re-add standard quotes around the found nickname
            collected_parts.append(f'"{q.strip()}"')
      
      # 3. NESTED BOLD (e.g., inside a span)
      elif child.name == 'span':
        nested = child.find(['b', 'strong'])
        if nested:
          collected_parts.append(nested.get_text().strip())

    # Deduplicate while preserving order
    seen = set()
    unique_parts = [x for x in collected_parts if not (x in seen or seen.add(x))]
    
    # JOIN WITH THE REQUESTED DELIMITER
    full_name_candidate = " . ".join(unique_parts)
    
    # Cleanup citations and excessive whitespace
    full_name_candidate = re.sub(r'\[.*?\]', '', full_name_candidate)
    full_name_candidate = re.sub(r'\s+', ' ', full_name_candidate).strip()

    clean_input = original_name.lower().strip()
    clean_found = full_name_candidate.lower().strip()
    
    # 1. Name Check
    if clean_found and clean_found != clean_input: 
      # Safety Check for fuzzy match relevance
      input_words = set(re.findall(r'\w+', clean_input))
      found_words = set(re.findall(r'\w+', clean_found))
      
      # If no shared words, flag it
      if not input_words.intersection(found_words):
        return full_name_candidate, "WARN:NAME_MISMATCH", birth_date

      return full_name_candidate, "FOUND_NEW_NAME", birth_date

    return "", "MATCHES_INPUT", birth_date

  except Exception as e:
    return "", f"ERROR: {e}", ""

# --- HELPER: SEARCH STRATEGY ---
def find_best_slug(name):
  try:
    params = { "action": "opensearch", "search": name, "limit": 1, "namespace": 0, "format": "json" }
    # timeout=30 seconds
    resp = requests.get(WIKI_API_URL, params=params, headers={'User-Agent': 'Bot/1.0'}, timeout=30)
    data = resp.json()
    
    if not data[1]:
      return ""
    
    best_match_title = data[1][0]
    return get_canonical_slug_from_api(best_match_title)
  except: 
    return ""

# ==========================================
# 3. INCREMENTAL EXECUTION LOOP
# ==========================================

total_rows = len(df)
fieldnames = ["NAME", "Full Name", "born", "wikipedia", "SOURCE", "STATUS"]

# Initialize processing flag based on START_FROM_NAME
# If START_FROM_NAME is empty, start immediately (True).
# If it has a value, start paused (False).
start_processing = False if START_FROM_NAME else True

print(f"Starting Safer Scan on {total_rows} rows...")
if not start_processing:
    print(f"NOTE: Skipping rows until NAME matches: '{START_FROM_NAME}'")

with open(CSV_OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as csv_file:
  writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
  writer.writeheader()
  
  for index, row in df.iterrows():
    name = str(row['NAME'])
    
    # --- SKIP LOGIC CHECK ---
    # We check this FIRST. If we haven't found the start name yet,
    # we skip the entire processing logic and the writing logic.
    if not start_processing:
        if name == START_FROM_NAME:
            start_processing = True
            print(f"\n---> MATCH FOUND: {name}. Resuming scrape from here.")
        else:
            # Skip this iteration entirely (no write to CSV)
            continue

    # --- MAIN PROCESSING ---
    sheet_full_name = str(row.get('Full Name', '')).strip()
    sheet_birth_date = str(row.get('born', '')).strip()
    sheet_slug = str(row.get('wikipedia', '')).strip()

    has_full_name = bool(sheet_full_name)
    has_birth_date = bool(sheet_birth_date)

    row_data = {
      "NAME": name,
      "Full Name": sheet_full_name,
      "born": sheet_birth_date,
      "wikipedia": sheet_slug,
      "SOURCE": "",
      "STATUS": ""
    }

    # --- PATH 1: HAS SLUG -> SKIP EVERYTHING ---
    if sheet_slug:
      row_data["STATUS"] = "PASSED (EXISTING SLUG)"
      row_data["SOURCE"] = "GSHEET"
      writer.writerow(row_data)
      csv_file.flush()
      continue

    # --- PATH 2: NO SLUG -> SEARCH ---
    print(f"[{index}/{total_rows}] Searching: {name}...", end="\r")
    
    slug_to_use = ""
    source_method = ""

    # Find new slug (Fuzzy + Resolve)
    slug_to_use = find_best_slug(name)
    source_method = "API"

    if slug_to_use:
      found_name, status, found_date = scrape_wiki_page(slug_to_use, name)
      
      # Update Row
      row_data["wikipedia"] = slug_to_use
      row_data["SOURCE"] = source_method

      status_parts = []
      if "WARN:" in status:
        status_parts.append(status)

      if not has_full_name and found_name:
        row_data["Full Name"] = found_name
        status_parts.append("FOUND_NAME")

      if not has_birth_date and found_date:
        row_data["born"] = found_date
        status_parts.append("FOUND_DATE")

      if status == "404_NOT_FOUND" or status == "DISAMBIGUATION_PAGE":
        row_data["STATUS"] = status
      else:
        row_data["STATUS"] = " & ".join(status_parts) if status_parts else "REVIEW_NO_NEW_DATA"

    else:
      row_data["SOURCE"] = "FAILED_SEARCH"
      row_data["STATUS"] = "NO_URL"

    # Write ONLY if we are processing (which we are, if we passed the check above)
    writer.writerow(row_data)
    csv_file.flush() 
    
    # Consistent sleep
    time.sleep(0.5)

print(f"\nDone. Processed rows saved to {CSV_OUTPUT_FILE}")