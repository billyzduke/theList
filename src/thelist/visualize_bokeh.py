import pandas as pd
import numpy as np
import os
import time
import unicodedata
from bokeh.io import save, output_file
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool, LabelSet, CustomJS, TapTool
from bokeh.palettes import Inferno256
from bokeh.transform import linear_cmap

# ==========================================
# 1. CONFIGURATION
# ==========================================
LIST_PATH = '/Volumes/Moana/Dropbox/inhumantouch.art/@importantstuff/theList'
DATA_PATH = 'data'
VIS_PATH = 'visualizations'
CSV_FILE = 'blend-data.csv'

# Construct Paths
CSV_FILE_PATH = os.path.join(LIST_PATH, DATA_PATH, CSV_FILE)
TIMESTAMP = time.strftime("%Y%m%d-%H%M%S")
VIS_FILE = f'chord_pro_{TIMESTAMP}.html'
VIS_FILE_PATH = os.path.join(LIST_PATH, VIS_PATH, VIS_FILE)

# ==========================================
# 2. DATA PREP & CLEANING
# ==========================================
def clean_string(s):
    if not isinstance(s, str): return str(s)
    s = unicodedata.normalize('NFKD', s)
    s = s.encode('ascii', 'ignore').decode('utf-8')
    s = s.replace("’", "'").replace("‘", "'")
    return s.strip()

print("Loading Data...")
if not os.path.exists(CSV_FILE_PATH):
    print(f"Error: {CSV_FILE_PATH} not found.")
    exit()

df = pd.read_csv(CSV_FILE_PATH)
df['Source'] = df['Source'].apply(clean_string)
df['Target'] = df['Target'].apply(clean_string)

# Calculate Popularity (Degree)
sources = df['Source'].value_counts()
targets = df['Target'].value_counts()
degree_counts = sources.add(targets, fill_value=0).sort_values(ascending=False)
sorted_names = degree_counts.index.tolist()

print(f"Found {len(sorted_names)} unique nodes.")

# Build Partner Lists for Tooltips
adjacency = {name: [] for name in sorted_names}
for _, row in df.iterrows():
    s, t = row['Source'], row['Target']
    if s in adjacency: adjacency[s].append(t)
    if t in adjacency: adjacency[t].append(s)

node_metadata = {}
for name in sorted_names:
    partners = sorted(adjacency[name])
    # Wrap text for tooltip if it's too long
    p_str = ", ".join(partners)
    node_metadata[name] = {
        'popularity': int(degree_counts[name]),
        'partners': p_str
    }

# Color Palette Logic (Inferno)
# Map index to Inferno256
palette_step = len(Inferno256) // len(sorted_names)
# Reverse Inferno so popular = bright/yellow, less popular = dark/purple (or vice versa)
# Standard Inferno: 0=Black, 256=Yellow. 
# Let's make popular nodes brighter.
colors = [Inferno256[min(i * palette_step, 255)] for i in range(len(sorted_names))]
node_color_map = dict(zip(sorted_names, colors)) 
# If you prefer top items to be Purple and bottom Yellow, reverse `colors`.

# ==========================================
# 3. GEOMETRY ENGINE (The Math)
# ==========================================
def calculate_chord_layout(nodes, links_df):
    # Layout Config
    padding = 0.05
    total_space = 2 * np.pi - (len(nodes) * padding)
    arc_len = total_space / len(nodes) # Equal width arcs for cleanness
    
    current_angle = 0
    node_geometry = []
    node_angles = {} # Store mid-points for link calculation

    for node in nodes:
        start = current_angle
        end = current_angle + arc_len
        mid = (start + end) / 2
        node_angles[node] = mid
        
        # Metadata
        meta = node_metadata.get(node, {'popularity': 0, 'partners': ''})
        
        # Label Geometry
        # We push labels slightly out (radius 1.15)
        # We flip text on the left side (90 to 270 degrees) so it's readable
        mid_deg = np.degrees(mid)
        if 90 < mid_deg < 270:
            text_align = 'right'
            text_angle = mid + np.pi # Flip 180
            # Offset logic for left side
            lx = 1.15 * np.cos(mid)
            ly = 1.15 * np.sin(mid)
        else:
            text_align = 'left'
            text_angle = mid
            lx = 1.15 * np.cos(mid)
            ly = 1.15 * np.sin(mid)

        node_geometry.append({
            'name': node,
            'start_angle': start,
            'end_angle': end,
            'color': node_color_map[node],
            'popularity': meta['popularity'],
            'partners_list': meta['partners'],
            'label_x': lx,
            'label_y': ly,
            'text_angle': text_angle,
            'text_align': text_align
        })
        current_angle = end + padding

    # Link Geometry (Bezier)
    link_geometry = []
    for _, row in links_df.iterrows():
        src, tgt = row['Source'], row['Target']
        if src not in node_angles or tgt not in node_angles: continue
        
        a1, a2 = node_angles[src], node_angles[tgt]
        x0, y0 = np.cos(a1), np.sin(a1)
        x1, y1 = np.cos(a2), np.sin(a2)
        
        # Curvature: Control point (0,0) makes perfect circular chords
        link_geometry.append({
            'source_name': src,
            'target_name': tgt,
            'x0': x0, 'y0': y0,
            'x1': x1, 'y1': y1,
            'cx': 0, 'cy': 0,
            'color': node_color_map[src] # Link takes Source color
        })
        
    return pd.DataFrame(node_geometry), pd.DataFrame(link_geometry)

print("Calculating Geometry...")
nodes_df, links_df = calculate_chord_layout(sorted_names, df)

# ==========================================
# 4. BOKEH PLOTTING
# ==========================================
node_source = ColumnDataSource(nodes_df)
link_source = ColumnDataSource(links_df)

# Setup Canvas
p = figure(
    width=1100, height=1100,
    x_range=(-1.8, 1.8), y_range=(-1.8, 1.8), # More space for labels
    title=None,
    toolbar_location=None, tools=""
)
# Dark Mode Styling
p.background_fill_color = "#181818"
p.border_fill_color = "#181818"
p.outline_line_color = None
p.axis.visible = False
p.grid.visible = False

# A. LINKS (Behind)
links_renderer = p.quadratic_bezier(
    x0="x0", y0="y0", x1="x1", y1="y1", cx="cx", cy="cy",
    source=link_source,
    line_color="color",
    line_width=2,
    line_alpha=0.2, # Default alpha
    hover_line_alpha=0.8, # Ignored by CustomJS, but good hygiene
)

# B. NODES (Visible)
nodes_renderer = p.annular_wedge(
    x=0, y=0, inner_radius=1.0, outer_radius=1.08,
    start_angle="start_angle", end_angle="end_angle",
    fill_color="color", line_color=None,
    source=node_source,
    name="nodes_visible"
)

# C. HITBOXES (Invisible - Covers text area)
# This extends from the node out to where the text ends
hitbox_renderer = p.annular_wedge(
    x=0, y=0, inner_radius=1.0, outer_radius=1.6, # Wide radius to catch text
    start_angle="start_angle", end_angle="end_angle",
    fill_color="white", fill_alpha=0.0, line_alpha=0.0, # Invisible
    source=node_source,
    name="nodes_hitbox"
)

# D. LABELS
labels = LabelSet(
    x='label_x', y='label_y', text='name',
    angle='text_angle', text_align='text_align',
    text_baseline='middle',
    text_font_size='9pt', text_color='#999999',
    source=node_source, render_mode='canvas'
)
p.add_layout(labels)

# ==========================================
# 5. INTERACTION (JS & TOOLTIP)
# ==========================================

# The Exact Tooltip HTML you provided
tooltip_html = """
<div style="background-color:#333; color:#eee; padding:10px; border-radius:5px; border:1px solid #555; min-width:150px; max-width:300px;">
    <span style="font-size: 16px; font-weight: bold; color: #fff;">@name</span>
    <br>
    <span style="font-size: 12px; color: #ff5555;">Connections: @popularity</span>
    <hr style="border: 0; border-top: 1px solid #555; margin: 5px 0;">
    <span style="font-size: 11px; color: #bbb;">Connected To:</span><br>
    <span style="font-size: 11px; color: #ddd; line-height: 1.2;">@partners_list</span>
</div>
"""

# CustomJS: Handles highlighting links when Node OR Hitbox is hovered
code_hover = """
    const links = link_source.data;
    const nodes = node_source.data;
    
    // Get indices of hovered item
    const indices = cb_data.index.indices;
    
    // RESET all links to default
    for (let i = 0; i < links['source_name'].length; i++) {
        links['line_alpha'][i] = 0.2;
        links['line_width'][i] = 2;
    }

    // If hovering...
    if (indices.length > 0) {
        const idx = indices[0];
        const hovered_name = nodes['name'][idx];

        // Highlight connected links
        for (let i = 0; i < links['source_name'].length; i++) {
            if (links['source_name'][i] == hovered_name || links['target_name'][i] == hovered_name) {
                links['line_alpha'][i] = 0.9;
                links['line_width'][i] = 4;
            }
        }
        
        // Optional: Dim other nodes? (Not implemented to keep it clean)
    }

    link_source.change.emit();
"""

callback = CustomJS(args=dict(link_source=link_source, node_source=node_source), code=code_hover)

hover = HoverTool()
hover.tooltips = tooltip_html
# Attach hover to BOTH the visible nodes AND the invisible hitboxes
hover.renderers = [nodes_renderer, hitbox_renderer]
hover.callback = callback

p.add_tools(hover)

# ==========================================
# 6. SAVE & POST-PROCESS
# ==========================================
print(f"Saving to {VIS_FILE_PATH}...")
output_file(VIS_FILE_PATH)
save(p)

# HTML Injection for Background (The "Nuclear" styling fix)
with open(VIS_FILE_PATH, 'r', encoding='utf-8') as f:
    html_content = f.read()

style_injection = '<body style="background-color: #000000; margin: 0; display: flex; justify-content: center; align-items: center; height: 100vh;">'
html_content = html_content.replace('<body>', style_injection)

with open(VIS_FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Done.")