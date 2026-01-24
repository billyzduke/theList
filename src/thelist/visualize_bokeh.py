import pandas as pd
import numpy as np
import os
import time
import unicodedata
from bokeh.io import save, output_file
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool, LabelSet, CustomJS, Div
from bokeh.layouts import row as bokeh_row 
from bokeh.palettes import Inferno256

# ==========================================
# 1. CONFIGURATION
# ==========================================
LIST_PATH = '/Volumes/Moana/Dropbox/inhumantouch.art/@importantstuff/theList'
DATA_PATH = 'data'
VIS_PATH = 'visualizations'
CSV_FILE = 'blend-data.csv'

CSV_FILE_PATH = os.path.join(LIST_PATH, DATA_PATH, CSV_FILE)
TIMESTAMP = time.strftime("%Y%m%d-%H%M%S")
VIS_FILE = f'chord_fisheye_final_{TIMESTAMP}.html'
VIS_FILE_PATH = os.path.join(LIST_PATH, VIS_PATH, VIS_FILE)

# ==========================================
# 2. DATA PREP
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

sources = df['Source'].value_counts()
targets = df['Target'].value_counts()
degree_counts = sources.add(targets, fill_value=0).sort_values(ascending=False)
sorted_names = degree_counts.index.tolist()

print(f"Processing {len(sorted_names)} nodes...")

adjacency = {name: [] for name in sorted_names}
for _, r in df.iterrows():
    s, t = r['Source'], r['Target']
    if s in adjacency: adjacency[s].append(t)
    if t in adjacency: adjacency[t].append(s)

node_metadata = {}
for name in sorted_names:
    partners = sorted(adjacency[name])
    p_str = ", ".join(partners)
    node_metadata[name] = {
        'popularity': int(degree_counts[name]),
        'partners': p_str
    }

palette_step = len(Inferno256) // len(sorted_names)
colors = [Inferno256[min(i * palette_step, 255)] for i in range(len(sorted_names))]
node_color_map = dict(zip(sorted_names, colors)) 

# ==========================================
# 3. GEOMETRY ENGINE
# ==========================================
def calculate_layout(nodes, links_df):
    padding = 0.02
    total_space = 2 * np.pi - (len(nodes) * padding)
    arc_len = total_space / len(nodes)
    
    current_angle = 0
    node_data = []
    node_angle_map = {} 

    # --- NODES ---
    for node in nodes:
        start = current_angle
        end = current_angle + arc_len
        mid = (start + end) / 2
        mid_norm = mid % (2 * np.pi)
        node_angle_map[node] = mid_norm
        
        meta = node_metadata.get(node, {'popularity': 0, 'partners': ''})
        
        # Base Radius
        radius = 1.15
        
        # Initial Alignment Calculation
        mid_deg = np.degrees(mid_norm)
        if 90 < mid_deg < 270:
            text_align = 'right'
            text_angle = mid + np.pi 
        else:
            text_align = 'left'
            text_angle = mid
        
        lx = radius * np.cos(mid)
        ly = radius * np.sin(mid)

        node_data.append({
            'name': node,
            'start_angle': start,
            'end_angle': end,
            'mid_angle': mid_norm, 
            'color': node_color_map[node],
            'popularity': meta['popularity'],
            'partners_list': meta['partners'],
            'label_x': lx,
            'label_y': ly,
            'base_x': lx, 
            'base_y': ly,
            'base_angle': mid_norm,
            'text_angle': text_angle,
            'base_text_angle': text_angle,
            'text_align': text_align,
            'font_size': '9px' 
        })
        current_angle = end + padding

    # --- LINKS ---
    link_data = []
    for _, link_row in links_df.iterrows():
        src, tgt = link_row['Source'], link_row['Target']
        if src not in node_angle_map or tgt not in node_angle_map: continue
        
        a1, a2 = node_angle_map[src], node_angle_map[tgt]
        c = "#999999" 
        
        link_data.append({
            'source_name': src,
            'target_name': tgt,
            'x0': np.cos(a1), 'y0': np.sin(a1),
            'x1': np.cos(a2), 'y1': np.sin(a2),
            'cx0': 0, 'cy0': 0, 'cx1': 0, 'cy1': 0,
            'color': c,
            'base_color': c, 
            'line_alpha': 0.4, 
            'line_width': 1
        })
        
    return pd.DataFrame(node_data), pd.DataFrame(link_data)

nodes_df, links_df = calculate_layout(sorted_names, df)

# ==========================================
# 4. PLOTTING SETUP
# ==========================================
node_source = ColumnDataSource(nodes_df)
link_source = ColumnDataSource(links_df)

info_div = Div(
    text="""<div style="color:#666; font-size:12px; font-family:sans-serif; text-align:center;">Hover for details</div>""",
    width=300, height=120,
    styles={'position': 'absolute', 'top': '20px', 'left': '20px', 'z-index': '100'}
)

p = figure(
    width=1100, height=1100,
    x_range=(-2.1, 2.1), y_range=(-2.1, 2.1), # Wider range prevents edge popping
    title=None, toolbar_location=None, tools=""
)
p.background_fill_color = "#101010"
p.border_fill_color = "#101010"
p.outline_line_color = None
p.axis.visible = False
p.grid.visible = False

# A. LINKS
p.bezier(
    x0="x0", y0="y0", x1="x1", y1="y1", 
    cx0="cx0", cy0="cy0", cx1="cx1", cy1="cy1",
    source=link_source,
    line_color="color", 
    line_width="line_width",
    line_alpha="line_alpha"
)

# B. NODES
p.annular_wedge(
    x=0, y=0, inner_radius=1.0, outer_radius=1.08,
    start_angle="start_angle", end_angle="end_angle",
    fill_color="color", line_color=None,
    source=node_source,
)

# C. HITBOXES
hitbox_renderer = p.annular_wedge(
    x=0, y=0, inner_radius=0.0, outer_radius=2.0, 
    start_angle="start_angle", end_angle="end_angle",
    fill_color="white", fill_alpha=0.0, line_alpha=0.0,
    source=node_source,
    name="hitbox"
)

# D. LABELS (Note: text_align is now bound to data for dynamic updates)
labels = LabelSet(
    x='label_x', y='label_y', text='name',
    angle='text_angle', text_align='text_align', # <--- DYNAMIC
    text_baseline='middle',
    text_font_size='font_size',
    text_color='#cccccc',
    source=node_source
)
p.add_layout(labels)

# ==========================================
# 5. JS LOGIC (Dynamic Alignment & Correction)
# ==========================================
code_hover = """
    const nodes = node_source.data;
    const links = link_source.data;
    
    if (!cb_data.geometry) return;
    
    const mx = cb_data.geometry.x;
    const my = cb_data.geometry.y;
    
    let m_angle = Math.atan2(my, mx);
    if (m_angle < 0) m_angle += 2 * Math.PI;
    
    // --- SETTINGS ---
    const ANGULAR_THRESHOLD = 0.5; 
    const BASE_SIZE = 9;
    const MAX_SIZE = 26; 
    const REPULSION_STRENGTH = 0.05; 
    
    // Find Anchor
    let min_dist = 1000;
    let closest_idx = -1;
    const n_len = nodes['name'].length;
    
    for (let i = 0; i < n_len; i++) {
        let diff = Math.abs(m_angle - nodes['base_angle'][i]);
        if (diff > Math.PI) diff = 2 * Math.PI - diff;
        if (diff < min_dist) {
            min_dist = diff;
            closest_idx = i;
        }
    }
    
    // LOOP NODES
    for (let i = 0; i < n_len; i++) {
        const base_angle = nodes['base_angle'][i];
        
        let diff = Math.abs(m_angle - base_angle);
        if (diff > Math.PI) diff = 2 * Math.PI - diff;

        if (diff < ANGULAR_THRESHOLD) {
            const ratio = diff / ANGULAR_THRESHOLD;
            const factor = 0.5 * (1 + Math.cos(ratio * Math.PI)); 
            
            // 1. RESIZE
            const new_size = BASE_SIZE + (MAX_SIZE - BASE_SIZE) * factor;
            nodes['font_size'][i] = new_size.toFixed(1) + "px";
            
            // 2. REPULSION
            let new_angle = base_angle;
            
            if (i !== closest_idx) {
                let signed_diff = base_angle - m_angle;
                while (signed_diff > Math.PI) signed_diff -= 2 * Math.PI;
                while (signed_diff < -Math.PI) signed_diff += 2 * Math.PI;
                
                const push = (signed_diff > 0 ? 1 : -1) * factor * REPULSION_STRENGTH;
                new_angle = base_angle + push;
            }
            
            // 3. POSITION (With Corrective Constant)
            // 1.15 is base. We subtract a tiny bit as it grows to keep visual center aligned.
            const radius = 1.15 - (factor * 0.005); 
            
            nodes['label_x'][i] = radius * Math.cos(new_angle);
            nodes['label_y'][i] = radius * Math.sin(new_angle);
            
            // 4. DYNAMIC ALIGNMENT (Fixes "Pop Inward")
            // Check if we are on Left or Right side of the circle
            const is_right = Math.cos(new_angle) >= 0;
            
            if (is_right) {
                nodes['text_align'][i] = 'left';
                nodes['text_angle'][i] = new_angle;
            } else {
                nodes['text_align'][i] = 'right';
                nodes['text_angle'][i] = new_angle + Math.PI;
            }

        } else {
            // Restore Defaults
            nodes['font_size'][i] = BASE_SIZE + "px";
            nodes['label_x'][i] = nodes['base_x'][i];
            nodes['label_y'][i] = nodes['base_y'][i];
            
            // Restore Base Angle/Alignment (avoids drift)
            const base_a = nodes['base_angle'][i];
            const is_right = Math.cos(base_a) >= 0;
            if (is_right) {
                nodes['text_align'][i] = 'left';
                nodes['text_angle'][i] = base_a;
            } else {
                nodes['text_align'][i] = 'right';
                nodes['text_angle'][i] = base_a + Math.PI;
            }
        }
    }
    
    // --- HIGHLIGHTING ---
    const l_len = links['source_name'].length;
    
    // Reset
    for (let k = 0; k < l_len; k++) {
        links['line_alpha'][k] = 0.4;
        links['line_width'][k] = 1;
        links['color'][k] = links['base_color'][k];
    }

    // Highlight
    if (closest_idx !== -1 && min_dist < (ANGULAR_THRESHOLD * 0.5)) {
        const active_name = nodes['name'][closest_idx];
        const active_pop = nodes['popularity'][closest_idx];
        const active_partners = nodes['partners_list'][closest_idx];

        for (let k = 0; k < l_len; k++) {
            if (links['source_name'][k] === active_name || links['target_name'][k] === active_name) {
                links['line_alpha'][k] = 0.9;
                links['line_width'][k] = 2;
                links['color'][k] = "#DDDDDD"; // New Highlight Color
            }
        }
        
        info_div.text = `
            <div style="background-color:rgba(20,20,20,0.9); padding:15px; border:1px solid #555; border-radius:8px; color:#eee; font-family:Helvetica, sans-serif;">
                <div style="font-size:20px; font-weight:bold; color:#fff; margin-bottom:5px;">${active_name}</div>
                <div style="font-size:12px; color:#ff7777; margin-bottom:8px;">Connections: ${active_pop}</div>
                <div style="font-size:11px; color:#aaa; line-height:1.4;">${active_partners}</div>
            </div>
        `;
    } else {
        info_div.text = "";
    }

    node_source.change.emit();
    link_source.change.emit();
"""

callback = CustomJS(
    args=dict(node_source=node_source, link_source=link_source, info_div=info_div), 
    code=code_hover
)

hover = HoverTool(
    tooltips=None, 
    callback=callback, 
    renderers=[hitbox_renderer],
    mode='mouse'
)

p.add_tools(hover)
layout = bokeh_row(p, info_div) 

print(f"Saving to {VIS_FILE_PATH}...")
output_file(VIS_FILE_PATH)
save(layout)

# HTML INJECTION
with open(VIS_FILE_PATH, 'r', encoding='utf-8') as f:
    html_content = f.read()

extra_css = """
<style>
    body { background-color: #101010; margin: 0; overflow: hidden; }
    .bk-root .bk-div { 
        position: fixed !important; 
        top: 20px !important; 
        left: 20px !important; 
        pointer-events: none; 
    }
</style>
"""

html_content = html_content.replace('</head>', f'{extra_css}</head>')

with open(VIS_FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Done.")