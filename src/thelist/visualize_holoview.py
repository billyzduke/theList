import pandas as pd
import holoviews as hv
from holoviews import opts
from bokeh.models import HoverTool, CustomJS  # <--- Added CustomJS
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
csv_file_path = os.path.join(list_path, data_path, csv_file)

# --- CLEANER ---
def clean_string(s):
  if not isinstance(s, str):
    return str(s)
  s = unicodedata.normalize('NFKD', s)
  s = s.encode('ascii', 'ignore').decode('utf-8')
  s = s.replace("’", "'").replace("‘", "'")
  return s.strip()

## --- HOOK: Sync Data & Sync Highlights (The "Nuclear" Fix) ---
def hook(plot, element):
    # 1. Fix the Background
    plot.state.border_fill_color = '#181818'
    plot.state.outline_line_color = None 
    
    # 2. Find components
    graph_renderer = None
    text_renderer = None
    hover_tool = None
    
    for r in plot.state.renderers:
        if hasattr(r, 'glyph') and hasattr(r.glyph, 'text'):
            text_renderer = r
        if hasattr(r, 'node_renderer'):
            graph_renderer = r
            
    for t in plot.state.tools:
        if isinstance(t, HoverTool):
            hover_tool = t

    if text_renderer and graph_renderer and hover_tool:
        # --- PART A: Data Smuggling ---
        node_source = graph_renderer.node_renderer.data_source
        text_source = text_renderer.data_source
        
        for col in ['popularity', 'partners_list', 'name']:
            if col in node_source.data:
                text_source.data[col] = node_source.data[col]
        
        # --- PART B: The Javascript Linker ---
        # We force the graph to update by hitting every 'change' signal we can find.
        code = """
            const indices = cb_data.index.indices;
            const node_renderer = graph_renderer.node_renderer;
            const node_ds = node_renderer.data_source;
            
            // 1. Update the inspection
            if (indices.length > 0) {
                node_ds.inspected.indices = indices;
                node_renderer.inspected.indices = indices;
            } else {
                node_ds.inspected.indices = [];
                node_renderer.inspected.indices = [];
            }
            
            // 2. THE NUCLEAR OPTION: Fire signals on everything
            node_ds.change.emit();
            node_renderer.change.emit();
            graph_renderer.change.emit();
        """
        
        hover_tool.callback = CustomJS(args={'graph_renderer': graph_renderer}, code=code)
        
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

# 3. BUILD PARTNER LISTS
print("Aggregating partner lists...")
adjacency = {name: [] for name in sorted_names}

for _, row in df.iterrows():
  s, t = row['Source'], row['Target']
  if s in adjacency: adjacency[s].append(t)
  if t in adjacency: adjacency[t].append(s)

partner_strings = []
for name in sorted_names:
  partners = adjacency[name]
  partners.sort()
  p_str = ", ".join(partners)
  partner_strings.append(p_str)

# 4. PREPARE NODES
nodes = pd.DataFrame({
  'index': range(len(sorted_names)),
  'name': sorted_names,
  'group': 1,
  'popularity': degree_counts.values, 
  'partners_list': partner_strings
})
nodes_dataset = hv.Dataset(nodes, 'index', vdims=['name', 'popularity', 'partners_list'])

# 5. PREPARE LINKS
name_to_id = {name: i for i, name in enumerate(sorted_names)}
links = df[['Source', 'Target']].copy()
links['source_id'] = links['Source'].map(name_to_id)
links['target_id'] = links['Target'].map(name_to_id)
links['value'] = 1
links_final = links[['source_id', 'target_id', 'value']]

# 6. DEFINE TOOLTIP
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

print(f"Generating Interactive Chord Diagram...")

# 7. RENDER
chord = hv.Chord((links_final, nodes_dataset))

chord.opts(
  opts.Chord(
    tools=[hover],
    hooks=[hook],
    
    # Aesthetics
    cmap='Inferno',          
    node_color='popularity', 
    edge_color='source',   
    edge_cmap='Inferno',      
    edge_line_width=2,    
    edge_alpha=0.4,       
    
    # Size & Interaction
    node_size=6,              
    node_hover_fill_color='white', 
    
    labels='name',      
    label_text_font_size='9pt', 
    label_text_color='#999999', 
    
    width=1100,          
    height=1100,
    bgcolor='#333333'
  )
)

# 8. SAVE
vis_file_path = os.path.join(list_path, vis_path, vis_file)
print(f"Saving to {vis_file_path}...")
hv.save(chord, vis_file_path, resources='inline')

# 9. BACKGROUND FIX
with open(vis_file_path, 'r', encoding='utf-8') as f:
  html_content = f.read()

style_injection = '<body style="background-color: #000000; margin: 0; display: flex; justify-content: center; align-items: center; height: 100vh;">'
html_content = html_content.replace('<body>', style_injection)

with open(vis_file_path, 'w', encoding='utf-8') as f:
  f.write(html_content)

print(f"Done! Open {vis_file_path}")