import pandas as pd
import holoviews as hv
from holoviews import opts
from bokeh.models import HoverTool
import unicodedata
import os
import time

hv.extension('bokeh')

# --- CONFIG ---
list_path = '/Volumes/Moana/Dropbox/inhumantouch.art/@importantstuff/theList'
data_path = 'data'
vis_path = 'visualizations'
timestamp = time.strftime("%Y%m%d-%H%M%S")
vis_file = f'chord_{timestamp}.html'
csv_file = 'blend-data.csv'
csv_file_path = os.path.join(list_path, data_path, csv_file)# Make sure this matches your filename

# --- CLEANER ---
def clean_string(s):
  if not isinstance(s, str):
    return str(s)
  s = unicodedata.normalize('NFKD', s)
  s = s.encode('ascii', 'ignore').decode('utf-8')
  s = s.replace("’", "'").replace("‘", "'")
  return s.strip()

# --- HOOK: Fix Background & Sync ALL Data ---
def hook(plot, element):
    # 1. Fix the Background
    plot.state.border_fill_color = '#181818'
    plot.state.outline_line_color = None 
    
    # 2. Smuggle Data into the Labels
    graph_renderer = None
    text_renderer = None
    
    for r in plot.state.renderers:
        if hasattr(r, 'glyph') and hasattr(r.glyph, 'text'):
            text_renderer = r
        if hasattr(r, 'node_renderer'):
            graph_renderer = r
            
    if text_renderer and graph_renderer:
        node_data = graph_renderer.node_renderer.data_source.data
        text_data = text_renderer.data_source.data
        
        # We loop through the columns we want to sync
        # Added 'name' to this list so the label knows its own name!
        for col in ['popularity', 'partners_list', 'name']:
            if col in node_data:
                text_data[col] = node_data[col]
                
# 1. Load & Clean
if not os.path.exists(csv_file_path):
  print("Error: blend-data.csv not found.")
  exit()

df = pd.read_csv(csv_file_path)
df['Source'] = df['Source'].apply(clean_string)
df['Target'] = df['Target'].apply(clean_string)

# 2. POPULARITY SORTING
sources = df['Source'].value_counts()
targets = df['Target'].value_counts()
degree_counts = sources.add(targets, fill_value=0).sort_values(ascending=False)
sorted_names = degree_counts.index.tolist()

# 3. BUILD PARTNER LISTS (The New Step)
# We create a dictionary to hold the list of friends for every person
print("Aggregating partner lists...")
adjacency = {name: [] for name in sorted_names}

for _, row in df.iterrows():
  s, t = row['Source'], row['Target']
  # Add Target to Source's list
  if s in adjacency: 
    adjacency[s].append(t)
  # Add Source to Target's list (Undirected graph)
  if t in adjacency: 
    adjacency[t].append(s)

# Create a formatted string for the tooltip
# We join them with a comma and space
partner_strings = []
for name in sorted_names:
  partners = adjacency[name]
  partners.sort() # Alphabetize the friend list
  # formatting: "A, B, C"
  p_str = ", ".join(partners)
  partner_strings.append(p_str)

# 4. PREPARE NODES
nodes = pd.DataFrame({
  'index': range(len(sorted_names)),
  'name': sorted_names,
  'group': 1,
  'popularity': degree_counts.values, 
  'partners_list': partner_strings  # <--- Add the list to the dataset
})
nodes_dataset = hv.Dataset(nodes, 'index', vdims=['name', 'popularity', 'partners_list'])

# 5. PREPARE LINKS
name_to_id = {name: i for i, name in enumerate(sorted_names)}
links = df[['Source', 'Target']].copy()
links['source_id'] = links['Source'].map(name_to_id)
links['target_id'] = links['Target'].map(name_to_id)
links['value'] = 1
links_final = links[['source_id', 'target_id', 'value']]

# 6. DEFINE CUSTOM TOOLTIP (HTML)
# We use @name to pull from the column, @partners_list for the friends
tooltips = """
<div style="background-color:#333; color:#eee; padding:10px; border-radius:5px; border:1px solid #555; min-width:150px; max-width:300px;">
    <span style="font-size: 16px; font-weight: bold; color: #fff;">@name</span>
    <br>
    <span style="font-size: 12px; color: #ff5555;">Connections: @popularity</span>
    <hr style="border: 0; border-top: 1px solid #555; margin: 5px 0;">
    <span style="font-size: 11px; color: #bbb;">Connected To:</span><br>
    <span style="font-size: 11px; color: #ddd; line-height: 1.2;">@partners_list</span>
</div>
"""
hover = HoverTool(tooltips=tooltips)

print(f"Generating diagram with Partner Popups...")

# 7. RENDER
chord = hv.Chord((links_final, nodes_dataset))

chord.opts(
  opts.Chord(
    # Use our custom hover tool
    tools=[hover],
    hooks=[hook], 
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
    bgcolor='#333333',
  )
)

# 7. SAVE
vis_file_path = os.path.join(list_path, vis_path, vis_file)

print(f"Saving to {vis_file_path}...")
hv.save(chord, vis_file_path, resources='inline')

# 7. BACKGROUND FIX
with open(vis_file_path, 'r', encoding='utf-8') as f:
  html_content = f.read()

style_injection = '<body style="background-color: #000000; margin: 0; display: flex; justify-content: center; align-items: center; height: 100vh;">'
html_content = html_content.replace('<body>', style_injection)

with open(vis_file_path, 'w', encoding='utf-8') as f:
  f.write(html_content)

print(f"Done! Open {vis_file_path}")