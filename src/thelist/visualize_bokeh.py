import pandas as pd
import numpy as np
import os
import sys
import time
import json
import unicodedata
from bokeh.io import save, output_file
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool, LabelSet, CustomJS, Div
from bokeh.layouts import row as bokeh_row 
from bokeh.palettes import Inferno256, Turbo256

# ==========================================
# 1. CONFIGURATION
# ==========================================
LIST_PATH = '/Volumes/Moana/Dropbox/inhumantouch.art/@importantstuff/theList'
DATA_PATH = 'data'
VIS_PATH = 'visualizations'
CVS_EXT = '.csv'

if __name__ == "__main__":
  if len(sys.argv) > 1:
    CSV_FILE = sys.argv[1]
    if not str(CSV_FILE).endswith(CVS_EXT):
      CSV_FILE += CVS_EXT
  else:
    CSV_FILE = 'blend-data.csv'

csv_basename = os.path.splitext(os.path.basename(CSV_FILE))[0]
CSV_FILE_PATH = os.path.join(LIST_PATH, DATA_PATH, CSV_FILE)
TIMESTAMP = time.strftime("%Y%m%d-%H%M%S")
VIS_FILE = f'chord_{csv_basename}_{TIMESTAMP}.html'
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

print(f"Loading Data from {CSV_FILE}...")
if not os.path.exists(CSV_FILE_PATH):
  print(f"Error: {CSV_FILE_PATH} not found.")
  exit()

df = pd.read_csv(CSV_FILE_PATH)
df['Source'] = df['Source'].apply(clean_string)
df['Target'] = df['Target'].apply(clean_string)

sources = df['Source'].value_counts()
targets = df['Target'].value_counts()
degree_counts = sources.add(targets, fill_value=0)

sort_df = degree_counts.to_frame(name='count')
sort_df['name'] = sort_df.index
sort_df = sort_df.sort_values(by=['count', 'name'], ascending=[False, True])
sorted_names = sort_df.index.tolist()

name_to_index_map = {name: i for i, name in enumerate(sorted_names)}

print(f"Processing {len(sorted_names)} nodes...")

adjacency = {name: [] for name in sorted_names}
for _, r in df.iterrows():
  s, t = r['Source'], r['Target']
  if s in adjacency: adjacency[s].append(t)
  if t in adjacency: adjacency[t].append(s)

node_metadata = {}
for name in sorted_names:
  partners = sorted(adjacency[name])
  p_str = ",".join(partners)
  node_metadata[name] = {
      'popularity': int(degree_counts[name]),
      'partners': p_str
  }

# --- COLOR LOGIC (RAINBOW vs HEATMAP) ---
min_pop = sort_df['count'].min()
max_pop = sort_df['count'].max()

node_color_map = {}

if min_pop == max_pop:
    # CASE A: UNIFORM DATA (Zero Variance) -> RAINBOW MODE
    # Use Turbo256 for a nice wrapping spectrum
    print("  -> All nodes equal. Using Rainbow Spectrum.")
    palette = Turbo256 
    
    for i, name in enumerate(sorted_names):
        # Map color to Position (Index) instead of Popularity
        norm = i / max(1, len(sorted_names) - 1)
        idx = int(norm * (len(palette) - 1))
        node_color_map[name] = palette[idx]

else:
    # CASE B: VARIED DATA -> HEATMAP MODE
    # Inferno: 0=Dark, 255=Bright Yellow.
    # We want High Pop = Bright Yellow.
    # So we map Norm 1.0 -> Index 255.
    print("  -> Data varied. Using Heatmap (Bright=Popular).")
    
    # Slice off the bottom 50 (too dark)
    heatmap_palette = list(Inferno256)[50:]
    # DO NOT REVERSE. Standard Inferno is [Dark ... Bright]
    
    for name in sorted_names:
        pop = degree_counts[name]
        norm = (pop - min_pop) / (max_pop - min_pop)
        idx = int(norm * (len(heatmap_palette) - 1))
        node_color_map[name] = heatmap_palette[idx]

# ==========================================
# 3. GEOMETRY ENGINE
# ==========================================
def calculate_layout(nodes, links_df):
  # Dynamic Padding (Max 10% whitespace)
  total_circumference = 2 * np.pi
  max_total_padding = 0.10 * total_circumference
  
  calculated_padding = max_total_padding / len(nodes)
  padding = min(0.02, calculated_padding)
  
  total_space = total_circumference - (len(nodes) * padding)
  arc_len = total_space / len(nodes)
  
  current_angle = 0
  node_data = []
  node_angle_map = {} 
  
  r_inner = 1.0
  r_outer = 1.08

  for node in nodes:
    start = current_angle
    end = current_angle + arc_len
    mid = (start + end) / 2
    mid_norm = mid % (2 * np.pi)
    node_angle_map[node] = mid_norm
    
    meta = node_metadata.get(node, {'popularity': 0, 'partners': ''})
    
    # POLYGON GENERATION
    points = 15 
    angles = np.linspace(start, end, points)
    
    outer_xs = r_outer * np.cos(angles)
    outer_ys = r_outer * np.sin(angles)
    
    inner_xs = r_inner * np.cos(angles[::-1])
    inner_ys = r_inner * np.sin(angles[::-1])
    
    poly_xs = np.concatenate([outer_xs, inner_xs])
    poly_ys = np.concatenate([outer_ys, inner_ys])
    
    radius = 1.15
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
      'poly_xs': poly_xs,
      'poly_ys': poly_ys,
      'label_x': lx,
      'label_y': ly,
      'base_x': lx, 
      'base_y': ly,
      'base_angle': mid_norm,
      'text_angle': text_angle,
      'base_text_angle': text_angle,
      'text_align': text_align,
      'font_size': '9px',
      'text_color': '#666666'
    })
    current_angle = end + padding

  link_data = []
  for _, link_row in links_df.iterrows():
    src, tgt = link_row['Source'], link_row['Target']
    if src not in node_angle_map or tgt not in node_angle_map: continue
    
    a1, a2 = node_angle_map[src], node_angle_map[tgt]
    c = "#666666" 
    
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
  styles={'position': 'absolute', 'top': '20px', 'right': '20px', 'z-index': '100'}
)

p = figure(
  width=1100, height=1100,
  x_range=(-2.1, 2.1), y_range=(-2.1, 2.1),
  sizing_mode="scale_both", 
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

# B. NODES (PATCHES)
p.patches(
  xs="poly_xs", ys="poly_ys",
  fill_color="color", line_color=None,
  source=node_source
)

# C. HITBOXES
hitbox_renderer = p.annular_wedge(
  x=0, y=0, inner_radius=0.0, outer_radius=2.0, 
  start_angle="start_angle", end_angle="end_angle",
  fill_color="white", fill_alpha=0.0, line_alpha=0.0,
  source=node_source,
  name="hitbox"
)

# D. LABELS
labels = LabelSet(
  x='label_x', y='label_y', text='name',
  angle='text_angle', text_align='text_align',
  text_baseline='middle',
  text_font_size='font_size',
  text_color='text_color', 
  source=node_source
)
p.add_layout(labels)

# ==========================================
# 5. JS LOGIC
# ==========================================
name_map_json = json.dumps(name_to_index_map)

code_hover = f"""
  const nodes = node_source.data;
  const links = link_source.data;
  const name_map = {name_map_json};
  
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
  
  // COLOR HELPER
  function interpolateColor(factor) {{
      const base = 102; 
      const target = 170; 
      const val = Math.round(base + (target - base) * factor);
      return `rgb(${{val}}, ${{val}}, ${{val}})`;
  }}
  
  // 1. FIND MAIN ANCHOR
  let min_dist_mouse = 1000;
  let main_idx = -1;
  const n_len = nodes['name'].length;
  
  for (let i = 0; i < n_len; i++) {{
    let diff = Math.abs(m_angle - nodes['base_angle'][i]);
    if (diff > Math.PI) diff = 2 * Math.PI - diff;
    if (diff < min_dist_mouse) {{
      min_dist_mouse = diff;
      main_idx = i;
    }}
  }}
  
  // 2. IDENTIFY GRAVITY WELLS
  let primary_well = null;
  let all_wells = []; 
  
  if (main_idx !== -1 && min_dist_mouse < ANGULAR_THRESHOLD) {{
     primary_well = {{
        idx: main_idx,
        angle: nodes['base_angle'][main_idx]
     }};
     all_wells.push(primary_well);
     
     const p_str = nodes['partners_list'][main_idx];
     if (p_str && p_str.length > 0) {{
         const parts = p_str.split(',');
         for (let p_name of parts) {{
             let tidx = name_map[p_name];
             if (tidx !== undefined) {{
                 all_wells.push({{
                    idx: tidx,
                    angle: nodes['base_angle'][tidx]
                 }});
             }}
         }}
     }}
  }}
  
  // 3. APPLY LOGIC LOOP
  for (let i = 0; i < n_len; i++) {{
    const base_angle = nodes['base_angle'][i];
    
    // --- A. CALCULATE PHYSICS (HIGHEST MAGNIFICATION WINS) ---
    let max_factor = 0.0;
    let dominant_well_angle = base_angle; 
    
    for (let w of all_wells) {{
        let d = Math.abs(base_angle - w.angle);
        if (d > Math.PI) d = 2 * Math.PI - d;
        
        if (d < ANGULAR_THRESHOLD) {{
            const ratio = d / ANGULAR_THRESHOLD;
            const factor = 0.5 * (1 + Math.cos(ratio * Math.PI));
            
            if (factor > max_factor) {{
                max_factor = factor;
                dominant_well_angle = w.angle;
            }}
        }}
    }}
    
    // --- B. CALCULATE COLOR (LAYERED) ---
    let final_color = '#666666'; 
    
    if (primary_well) {{
        let d_prim = Math.abs(base_angle - primary_well.angle);
        if (d_prim > Math.PI) d_prim = 2 * Math.PI - d_prim;
        
        if (d_prim < ANGULAR_THRESHOLD) {{
            const ratio_p = d_prim / ANGULAR_THRESHOLD;
            const factor_p = 0.5 * (1 + Math.cos(ratio_p * Math.PI));
            final_color = interpolateColor(factor_p);
        }}
    }}
    
    if (primary_well && i === primary_well.idx) {{
        final_color = '#E6FFE6'; // Greenish
    }} else if (all_wells.length > 1) {{
        for (let k = 1; k < all_wells.length; k++) {{
            if (i === all_wells[k].idx) {{
                final_color = '#FFD1D1'; // Reddish
                break;
            }}
        }}
    }}
    
    // --- C. APPLY ATTRIBUTES ---
    if (max_factor > 0) {{
        const new_size = BASE_SIZE + (MAX_SIZE - BASE_SIZE) * max_factor;
        nodes['font_size'][i] = new_size.toFixed(1) + "px";
        nodes['text_color'][i] = final_color;
        
        let new_angle = base_angle;
        let is_center = false;
        for (let w of all_wells) {{ if (w.idx === i) is_center = true; }}
        
        if (!is_center) {{
            let signed_diff = base_angle - dominant_well_angle;
            while (signed_diff > Math.PI) signed_diff -= 2 * Math.PI;
            while (signed_diff < -Math.PI) signed_diff += 2 * Math.PI;
            
            const push = (signed_diff > 0 ? 1 : -1) * max_factor * REPULSION_STRENGTH;
            new_angle = base_angle + push;
        }}
        
        const radius = 1.15 - (max_factor * 0.005);
        nodes['label_x'][i] = radius * Math.cos(new_angle);
        nodes['label_y'][i] = radius * Math.sin(new_angle);
        
        const is_right = Math.cos(new_angle) >= 0;
        if (is_right) {{
            nodes['text_align'][i] = 'left';
            nodes['text_angle'][i] = new_angle;
        }} else {{
            nodes['text_align'][i] = 'right';
            nodes['text_angle'][i] = new_angle + Math.PI;
        }}
        
    }} else {{
        nodes['font_size'][i] = BASE_SIZE + "px";
        nodes['text_color'][i] = '#666666';
        nodes['label_x'][i] = nodes['base_x'][i];
        nodes['label_y'][i] = nodes['base_y'][i];
        
        const base_a = nodes['base_angle'][i];
        const is_right = Math.cos(base_a) >= 0;
        if (is_right) {{
            nodes['text_align'][i] = 'left';
            nodes['text_angle'][i] = base_a;
        }} else {{
            nodes['text_align'][i] = 'right';
            nodes['text_angle'][i] = base_a + Math.PI;
        }}
    }}
  }}
  
  // --- HIGHLIGHTING ---
  const l_len = links['source_name'].length;
  
  for (let k = 0; k < l_len; k++) {{
    links['line_alpha'][k] = 0.4;
    links['line_width'][k] = 1;
    links['color'][k] = links['base_color'][k];
  }}

  if (primary_well) {{
    const active_name = nodes['name'][main_idx];
    const active_pop = nodes['popularity'][main_idx];
    const active_partners = nodes['partners_list'][main_idx];

    for (let k = 0; k < l_len; k++) {{
      if (links['source_name'][k] === active_name || links['target_name'][k] === active_name) {{
        links['line_alpha'][k] = 0.9;
        links['line_width'][k] = 2;
        links['color'][k] = "#DDDDDD";
      }}
    }}
    
    info_div.text = `
      <div style="background-color:rgba(20,20,20,0.9); padding:15px; border:1px solid #555; border-radius:8px; color:#eee; font-family:Helvetica, sans-serif;">
        <div style="font-size:20px; font-weight:bold; color:#fff; margin-bottom:5px;">${{active_name}}</div>
        <div style="font-size:12px; color:#ff7777; margin-bottom:8px;">Connections: ${{active_pop}}</div>
        <div style="font-size:11px; color:#aaa; line-height:1.4;">${{active_partners}}</div>
      </div>
    `;
  }} else {{
    info_div.text = "";
  }}

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
layout = bokeh_row(p, info_div, sizing_mode="stretch_both")

print(f"Saving to {VIS_FILE_PATH}...")
output_file(VIS_FILE_PATH)
save(layout)

# HTML INJECTION
with open(VIS_FILE_PATH, 'r', encoding='utf-8') as f:
  html_content = f.read()

extra_css = """
<style>
  html, body {
    height: 100%;
    width: 100%;
    margin: 0;
    padding: 0;
    background-color: #101010;
    overflow: hidden;
  }
  .bk-root {
    width: 100% !important;
    height: 100% !important;
    display: flex;
    justify-content: center;
    align-items: center;
  }
  .bk-root .bk-div { 
    position: fixed !important; 
    top: 20px !important; 
    right: 20px !important; 
    pointer-events: none; 
  }
</style>
"""

html_content = html_content.replace('</head>', f'{extra_css}</head>')

with open(VIS_FILE_PATH, 'w', encoding='utf-8') as f:
  f.write(html_content)

print(f"Done. Saved to {VIS_FILE}")