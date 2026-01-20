import pygsheets
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import urllib.parse
from datetime import datetime
import csv
import sys

# --- CONFIGURATION ---
CSV_OUTPUT_FILE = "wiki_audit.csv"
WIKI_API_URL = "https://en.wikipedia.org/w/api.php"

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
  # 1. Hidden 'bday' class
  bday_tag = soup.find(class_="bday")
  if bday_tag: return bday_tag.get_text().strip()

  # 2. Infobox text parse
  infobox = soup.find(class_="infobox")
  if infobox:
    for row in infobox.find_all("tr"):
      header = row.find("th")
      if header and "Born" in header.get_text():
        data = row.find("td")
        if data:
          text = data.get_text(" ", strip=True).replace('\xa0', ' ')
          text = re.sub(r'\[.*?\]', '', text)
          
          # Match: "10 June 1967"
          match_dmy = re.search(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', text)
          if match_dmy:
            try: return datetime.strptime(match_dmy.group(0), "%d %B %Y").strftime("%Y-%m-%d")
            except: pass

          # Match: "June 10, 1967"
          match_mdy = re.search(r'([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})', text)
          if match_mdy:
            try: return datetime.strptime(match_mdy.group(0), "%B %d, %Y").strftime("%Y-%m-%d")
            except: pass

          # Match: Year Only
          year_match = re.search(r'\b(19\d{2}|20\d{2})\b', text)
          if year_match: return year_match.group(1)
  return ""

# --- HELPER: NAME SIMILARITY CHECK ---
def check_name_similarity(input_name, found_name):
    """
    Returns True if the names share at least one significant word.
    Helps catch bad fuzzy searches (e.g. 'Alicia' vs 'Bully').
    """
    def clean(n): return set(re.findall(r'\w+', n.lower()))
    input_set = clean(input_name)
    found_set = clean(found_name)
    
    # Remove common filler words if you want strictness, but usually fine.
    common = input_set.intersection(found_set)
    return len(common) > 0

# --- HELPER: SCRAPER ---
def scrape_wiki_page(url, original_name):
  session = requests.Session()
  session.headers.update({'User-Agent': 'Bot/1.0 (Researching internal data consistency)'})

  try:
    page_resp = session.get(url) 
    
    # --- CAPTURE FINAL URL (The "Bully" Fix) ---
    final_url = page_resp.url
    final_slug = ""
    if "/wiki/" in final_url:
      final_slug = urllib.parse.unquote(final_url.split("/wiki/")[-1])
    else:
      final_slug = url.split("/wiki/")[-1] if "/wiki/" in url else ""

    if page_resp.status_code != 200:
      return "", "404_NOT_FOUND", final_slug, ""
      
    soup = BeautifulSoup(page_resp.content, 'html.parser')
    
    if "may refer to:" in soup.get_text()[:500]:
      return "", "DISAMBIGUATION_PAGE", final_slug, ""

    birth_date = extract_birth_date(soup)

    content_div = soup.find(id="mw-content-text")
    if not content_div: return "", "NO_CONTENT", final_slug, birth_date

    paragraphs = content_div.select("div.mw-parser-output > p")
    target_p = None
    for p in paragraphs:
      text = p.get_text().strip()
      if text and not p.find('span', {'id': 'coordinates'}):
        target_p = p
        break
    
    if not target_p: return "", "NO_PARAGRAPH", final_slug, birth_date

    # --- NAME PARSING ---
    collected_parts = []
    for child in target_p.children:
      if isinstance(child, str) and '(' in child: break
      if child.name is None and '(' in str(child): break

      if child.name in ['b', 'strong']:
        text = child.get_text().strip()
        if text: collected_parts.append(text)
      elif isinstance(child, str) or child.name is None:
        quotes = re.findall(r'["“](.*?)["”]', str(child))
        for q in quotes: 
          if q.strip(): collected_parts.append(f'"{q.strip()}"')
      elif child.name == 'span':
        nested = child.find(['b', 'strong'])
        if nested: collected_parts.append(nested.get_text().strip())

    seen = set()
    unique_parts = [x for x in collected_parts if not (x in seen or seen.add(x))]
    full_name_candidate = " ".join(unique_parts)
    full_name_candidate = re.sub(r'\[.*?\]', '', full_name_candidate)
    full_name_candidate = re.sub(r'\s+', ' ', full_name_candidate).strip()

    clean_input = original_name.lower().strip()
    clean_found = full_name_candidate.lower().strip()
    
    # 1. Exact Match (No new data, but valid page)
    if clean_found == clean_input: 
        return "", "MATCHES_INPUT", final_slug, birth_date
        
    # 2. New Name Found
    if clean_found:
        # SAFETY CHECK: Do the names look related?
        if not check_name_similarity(original_name, full_name_candidate):
             # Return the name but Flag it
             return full_name_candidate, "WARN:NAME_MISMATCH", final_slug, birth_date
        
        return full_name_candidate, "FOUND_NEW_NAME", final_slug, birth_date

    return "", "NO_BOLD_NAME", final_slug, birth_date

  except Exception as e:
    return "", f"ERROR: {e}", "", ""

# --- HELPER: API ---
def get_wiki_url_from_api(search_query):
  try:
    params = { "action": "opensearch", "search": search_query, "limit": 1, "namespace": 0, "format": "json" }
    resp = requests.get(WIKI_API_URL, params=params, headers={'User-Agent': 'Bot/1.0'})
    data = resp.json()
    if data[1]: return data[3][0], data[3][0].split("/wiki/")[-1]
  except: pass
  return "", ""

# ==========================================
# 3. INCREMENTAL EXECUTION LOOP
# ==========================================

total_rows = len(df)
fieldnames = ["NAME", "Full Name", "born", "wikipedia", "SOURCE", "STATUS"]

print(f"Starting Smart Scan on {total_rows} rows...")

with open(CSV_OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    
    for index, row in df.iterrows():
        name = str(row['NAME'])
        
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

        # --- LOGIC GATE: PASS if we have everything ---
        if has_full_name and has_birth_date:
            row_data["SOURCE"] = "GSHEET"
            row_data["STATUS"] = "PASSED"
            writer.writerow(row_data)
            csv_file.flush()
            continue

        # --- SEARCH REQUIRED ---
        print(f"[{index}/{total_rows}] Searching: {name}...", end="\r")
        
        target_url, slug_used, source_method = "", "", ""

        if sheet_slug:
            target_url = f"https://en.wikipedia.org/wiki/{sheet_slug}"
            slug_used = sheet_slug
            source_method = "SLUG"
        else:
            target_url, slug_used = get_wiki_url_from_api(name)
            source_method = "API"

        if target_url:
            found_name, status, final_slug, found_date = scrape_wiki_page(target_url, name)
            
            # --- CONSOLE FEEDBACK FOR REDIRECTS ---
            if final_slug and final_slug != slug_used:
                print(f"[{index}] >>> Redirect: {slug_used} -> {final_slug}" + " "*20)

            # --- FORCE SLUG UPDATE ---
            # Even if name/date failed, if we have a final slug, USE IT.
            if final_slug:
                row_data["wikipedia"] = final_slug
            else:
                row_data["wikipedia"] = slug_used

            # --- FILL DATA ---
            status_parts = []
            
            # Add Warn flag if present
            if "WARN:" in status:
                status_parts.append(status) 

            if not has_full_name and found_name:
                row_data["Full Name"] = found_name
                status_parts.append("FOUND_NAME")

            if not has_birth_date and found_date:
                row_data["born"] = found_date
                status_parts.append("FOUND_DATE")

            row_data["SOURCE"] = source_method
            
            # Final Status Composition
            if status == "404_NOT_FOUND" or status == "DISAMBIGUATION_PAGE":
                row_data["STATUS"] = status
            else:
                row_data["STATUS"] = " & ".join(status_parts) if status_parts else "REVIEW_NO_NEW_DATA"

        else:
            row_data["SOURCE"] = "FAILED_SEARCH"
            row_data["STATUS"] = "NO_URL"

        writer.writerow(row_data)
        csv_file.flush() 
        
        if source_method == "API": time.sleep(0.5)
        else: time.sleep(0.1)

print(f"\nDone. All rows processed and saved to {CSV_OUTPUT_FILE}")