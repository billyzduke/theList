import pandas as pd
import holoviews as hv
from holoviews import opts
import unicodedata
import os
import time

hv.extension('bokeh')

# --- CONFIG ---
timestamp = int(time.time())
output_file = f'chord_{timestamp}.html'
csv_file = 'blend-data.csv'

# --- CLEANER ---
def clean_string(s):
  if not isinstance(s, str):
    return str(s)
  s = unicodedata.normalize('NFKD', s)
  s = s.encode('ascii', 'ignore').decode('utf-8')
  s = s.replace("’", "'").replace("‘", "'")
  return s.strip()

# 1. Load & Clean
if not os.path.exists(csv_file):
  print("Error: blend-data.csv not found.")
  exit()

df = pd.read_csv(csv_file)
df['Source'] = df['Source'].apply(clean_string)
df['Target'] = df['Target'].apply(clean_string)

# 2. POPULARITY SORTING
sources = df['Source'].value_counts()
targets = df['Target'].value_counts()
degree_counts = sources.add(targets, fill_value=0).sort_values(ascending=False)
sorted_names = degree_counts.index.tolist()

# 3. PREPARE NODES
nodes = pd.DataFrame({
  'index': range(len(sorted_names)),
  'name': sorted_names,
  'group': 1,
  'popularity': degree_counts.values 
})
nodes_dataset = hv.Dataset(nodes, 'index', vdims=['name', 'popularity'])

# 4. PREPARE LINKS
name_to_id = {name: i for i, name in enumerate(sorted_names)}
links = df[['Source', 'Target']].copy()
links['source_id'] = links['Source'].map(name_to_id)
links['target_id'] = links['Target'].map(name_to_id)
links['value'] = 1
links_final = links[['source_id', 'target_id', 'value']]

print(f"Generating Precision Diagram for {len(nodes)} nodes...")

# 5. RENDER
chord = hv.Chord((links_final, nodes_dataset))

chord.opts(
  opts.Chord(
    # --- PALETTE: INFERNO (Black -> Red -> Yellow) ---
    cmap='Inferno',          
    node_color='popularity', 
    
    # --- LINES ---
    edge_color='source',   
    edge_cmap='Inferno',      
    edge_line_width=2,    
    edge_alpha=0.4,       # Higher visibility
    
    # --- INTERACTION & SIZE ---
    node_size=6,              # <--- THE FIX (Prevents overlap)
    node_hover_fill_color='white', # confirm selection
    
    # --- LABELS ---
    labels='name',      
    label_text_font_size='9pt', 
    label_text_color='#999999', 
    
    width=1100,          
    height=1100,
    bgcolor='#333333'
  )
)

# 6. SAVE
print(f"Saving to {output_file}...")
hv.save(chord, output_file, resources='inline')

# 7. BACKGROUND FIX
with open(output_file, 'r', encoding='utf-8') as f:
  html_content = f.read()

style_injection = '<body style="background-color: #000000; margin: 0; display: flex; justify-content: center; align-items: center; height: 100vh;">'
html_content = html_content.replace('<body>', style_injection)

with open(output_file, 'w', encoding='utf-8') as f:
  f.write(html_content)

print(f"Done! Open {output_file}")