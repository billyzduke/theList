import pandas as pd
import numpy as np
import os
import sys
import time
import json
import unicodedata
import colorsys
from bokeh.io import save, output_file
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool, LabelSet, CustomJS
from bokeh.palettes import Inferno256

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

# --- COLOR LOGIC ---
min_pop = sort_df['count'].min()
max_pop = sort_df['count'].max()
node_color_map = {}

if min_pop == max_pop:
  print("  -> All nodes equal. Using Seamless HSV Cycle.")
  n_nodes = len(sorted_names)
  for i, name in enumerate(sorted_names):
    hue = i / n_nodes 
    rgb = colorsys.hsv_to_rgb(hue, 0.8, 0.9) 
    hex_color = '#%02x%02x%02x' % (int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))
    node_color_map[name] = hex_color
else:
  print("  -> Data varied. Using Heatmap.")
  heatmap_palette = list(Inferno256)[50:]
  for name in sorted_names:
    pop = degree_counts[name]
    norm = (pop - min_pop) / (max_pop - min_pop)
    idx = int(norm * (len(heatmap_palette) - 1))
    node_color_map[name] = heatmap_palette[idx]

# ==========================================
# 3. GEOMETRY ENGINE
# ==========================================
def calculate_layout(nodes, links_df):
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
      'base_text_align': text_align, # ADDED: Base align for reset
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
# KEY CHANGE: Added names to sources for JS lookup
node_source = ColumnDataSource(nodes_df, name="node_source")
link_source = ColumnDataSource(links_df, name="link_source")

p = figure(
  width=1100, height=1100,
  x_range=(-2.1, 2.1), y_range=(-2.1, 2.1),
  sizing_mode="stretch_both", 
  title=None, toolbar_location=None, tools=""
)
p.background_fill_color = "#101010"
p.border_fill_color = "#101010"
p.outline_line_color = None
p.axis.visible = False
p.grid.visible = False

p.bezier(
  x0="x0", y0="y0", x1="x1", y1="y1", 
  cx0="cx0", cy0="cy0", cx1="cx1", cy1="cy1",
  source=link_source,
  line_color="color", 
  line_width="line_width",
  line_alpha="line_alpha"
)

p.patches(
  xs="poly_xs", ys="poly_ys",
  fill_color="color", line_color=None,
  source=node_source
)

hitbox_renderer = p.annular_wedge(
  x=0, y=0, inner_radius=0.0, outer_radius=2.0, 
  start_angle="start_angle", end_angle="end_angle",
  fill_color="white", fill_alpha=0.0, line_alpha=0.0,
  source=node_source,
  name="hitbox"
)

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
# 5. JS LOGIC (HOVER)
# ==========================================
name_map_json = json.dumps(name_to_index_map)

code_hover = f"""
  const nodes = node_source.data;
  const links = link_source.data;
  const name_map = {name_map_json};
  const panel = document.getElementById('details-panel');
  
  if (!cb_data.geometry) return;
  
  const mx = cb_data.geometry.x;
  const my = cb_data.geometry.y;
  let m_angle = Math.atan2(my, mx);
  if (m_angle < 0) m_angle += 2 * Math.PI;
  
  const ANGULAR_THRESHOLD = 0.5; 
  const BASE_SIZE = 9;
  const MAX_SIZE = 26; 
  const REPULSION_STRENGTH = 0.05; 
  
  function interpolateColor(factor) {{
    const base = 102; 
    const target = 170; 
    const val = Math.round(base + (target - base) * factor);
    return `rgb(${{val}}, ${{val}}, ${{val}})`;
  }}
  
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
  
  let primary_well = null;
  let all_wells = []; 
  
  if (main_idx !== -1 && min_dist_mouse < ANGULAR_THRESHOLD) {{
    primary_well = {{ idx: main_idx, angle: nodes['base_angle'][main_idx] }};
    all_wells.push(primary_well);
    const p_str = nodes['partners_list'][main_idx];
    if (p_str && p_str.length > 0) {{
      const parts = p_str.split(',');
      for (let p_name of parts) {{
        let tidx = name_map[p_name];
        if (tidx !== undefined) {{
          all_wells.push({{ idx: tidx, angle: nodes['base_angle'][tidx] }});
        }}
      }}
    }}
  }}
  
  for (let i = 0; i < n_len; i++) {{
    const base_angle = nodes['base_angle'][i];
    let max_factor = 0.0;
    let dominant_well_angle = base_angle; 
    
    for (let w of all_wells) {{
      let d = Math.abs(base_angle - w.angle);
      if (d > Math.PI) d = 2 * Math.PI - d;
      if (d < ANGULAR_THRESHOLD) {{
        const ratio = d / ANGULAR_THRESHOLD;
        const factor = 0.5 * (1 + Math.cos(ratio * Math.PI));
        if (factor > max_factor) {{ max_factor = factor; dominant_well_angle = w.angle; }}
      }}
    }}
    
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
    if (primary_well && i === primary_well.idx) final_color = '#E6FFE6';
    else if (all_wells.length > 1) {{
      for (let k = 1; k < all_wells.length; k++) {{
        if (i === all_wells[k].idx) {{ final_color = '#FFD1D1'; break; }}
      }}
    }}
    
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
        nodes['text_align'][i] = 'left'; nodes['text_angle'][i] = new_angle;
      }} else {{
        nodes['text_align'][i] = 'right'; nodes['text_angle'][i] = new_angle + Math.PI;
      }}
    }} else {{
      nodes['font_size'][i] = BASE_SIZE + "px";
      nodes['text_color'][i] = '#666666';
      nodes['label_x'][i] = nodes['base_x'][i];
      nodes['label_y'][i] = nodes['base_y'][i];
      const base_a = nodes['base_angle'][i];
      const is_right = Math.cos(base_a) >= 0;
      if (is_right) {{
        nodes['text_align'][i] = 'left'; nodes['text_angle'][i] = base_a;
      }} else {{
        nodes['text_align'][i] = 'right'; nodes['text_angle'][i] = base_a + Math.PI;
      }}
    }}
  }}
  
  const l_len = links['source_name'].length;
  for (let k = 0; k < l_len; k++) {{
    links['line_alpha'][k] = 0.4;
    links['line_width'][k] = 1;
    links['color'][k] = links['base_color'][k];
  }}

  if (primary_well) {{
    const active_name = nodes['name'][main_idx];
    const p_str = nodes['partners_list'][main_idx];
    const partners = (p_str && p_str.length > 0) ? p_str.split(',') : [];

    for (let k = 0; k < l_len; k++) {{
      if (links['source_name'][k] === active_name || links['target_name'][k] === active_name) {{
        links['line_alpha'][k] = 0.9;
        links['line_width'][k] = 2;
        links['color'][k] = "#DDDDDD";
      }}
    }}
    
    if (panel) {{
      const isSidePanel = (window.innerWidth / window.innerHeight) > 1.4; 
      let svg_content = "";
      
      if (!isSidePanel) {{
        // === BOTTOM PANEL (Portrait) ===
        const panel_w = panel.clientWidth || window.innerWidth;
        const panel_h = panel.clientHeight || (window.innerHeight * 0.25);
        
        svg_content = `<svg width="100%" height="100%" style="font-family:Helvetica, sans-serif;">`;
        
        const prim_x = panel_w * 0.45; // Right aligned to 45%
        const part_x = panel_w * 0.55; // Left aligned to 55% (10% gap)
        
        const row_height = 40;
        const stack_height = (partners.length - 1) * row_height;
        const center_y = panel_h / 2;
        const start_y = center_y - (stack_height / 2);
        
        partners.forEach((p, idx) => {{
          const py = start_y + (idx * row_height);
          // Horizontal Bezier
          const path_d = `M ${{prim_x + 10}} ${{center_y}} C ${{prim_x + 30}} ${{center_y}}, ${{part_x - 30}} ${{py}}, ${{part_x - 10}} ${{py}}`;
          
          svg_content += `<path d="${{path_d}}" stroke="#DDDDDD" stroke-width="2" fill="none" opacity="0.9"/>`;
          svg_content += `<text x="${{part_x}}" y="${{py}}" fill="#FFD1D1" font-size="28px" text-anchor="start" alignment-baseline="middle" style="text-shadow: 0px 0px 3px rgba(0,0,0,0.8);">${{p}}</text>`;
        }});
        
        svg_content += `<text x="${{prim_x}}" y="${{center_y}}" fill="#E6FFE6" font-size="28px" font-weight="bold" text-anchor="end" alignment-baseline="middle" style="text-shadow: 0px 0px 4px rgba(0,0,0,0.8);">${{active_name}}</text>`;
        svg_content += `</svg>`;
         
      }} else {{
        // === SIDE PANEL (Landscape) ===
        const row_height = 40;
        const content_height = Math.max(200, partners.length * row_height + 100);
        const svg_height = content_height;
        
        const px_prim = 20;
        const py_prim = 40;
        const px_part = 150;
        const start_y = py_prim + 50;
        
        svg_content = `<svg width="100%" height="${{svg_height}}" style="font-family:Helvetica, sans-serif;">`;
        
        partners.forEach((p, idx) => {{
          const py = start_y + (idx * row_height);
          const path_d = `M ${{px_prim + 20}} ${{py_prim + 10}} C ${{px_prim + 20}} ${{py_prim + 50}}, ${{px_part - 50}} ${{py}}, ${{px_part}} ${{py}}`;
          svg_content += `<path d="${{path_d}}" stroke="#DDDDDD" stroke-width="2" fill="none" opacity="0.9"/>`;
          svg_content += `<text x="${{px_part + 10}}" y="${{py}}" fill="#FFD1D1" font-size="28px" alignment-baseline="middle" style="text-shadow: 0px 0px 3px rgba(0,0,0,0.8);">${{p}}</text>`;
        }});
        
        svg_content += `<text x="${{px_prim}}" y="${{py_prim}}" fill="#E6FFE6" font-size="28px" font-weight="bold" alignment-baseline="middle" text-anchor="start" style="text-shadow: 0px 0px 4px rgba(0,0,0,0.8);">${{active_name}}</text>`;
        svg_content += `</svg>`;
      }}
      panel.innerHTML = svg_content;
    }}
    
  }} else {{
    if (panel) {{
      panel.innerHTML = "";
    }}
  }}

  node_source.change.emit();
  link_source.change.emit();
"""

callback = CustomJS(
  args=dict(node_source=node_source, link_source=link_source), 
  code=code_hover
)

hover = HoverTool(
  tooltips=None, 
  callback=callback, 
  renderers=[hitbox_renderer],
  mode='mouse'
)

p.add_tools(hover)

print(f"Saving to {VIS_FILE_PATH}...")
output_file(VIS_FILE_PATH)
save(p) 

# ==========================================
# 6. HTML INJECTION (RESIZE + RESET)
# ==========================================
with open(VIS_FILE_PATH, 'r', encoding='utf-8') as f:
  html_content = f.read()

body_idx = html_content.find('</body>') 
if body_idx != -1:
  insert_html = '<div id="details-panel"></div>'
  
  # KEY CHANGE: Global Reset Script for Window Resize
  resize_script = """
  <script>
    window.addEventListener('resize', function() {
      // 1. Clear Panel
      var panel = document.getElementById('details-panel');
      if(panel) panel.innerHTML = '';

      // 2. Reset Bokeh Graph Sources
      if (typeof Bokeh !== 'undefined' && Bokeh.documents && Bokeh.documents.length > 0) {
        var doc = Bokeh.documents[0];
        var nodes = doc.get_model_by_name('node_source');
        var links = doc.get_model_by_name('link_source');

        if (nodes && links) {
          // RESET NODES
          var n_len = nodes.data['name'].length;
          for (var i = 0; i < n_len; i++) {
            nodes.data['text_color'][i] = '#666666';
            nodes.data['font_size'][i] = '9px';
            // Restore Base Geometry
            nodes.data['label_x'][i] = nodes.data['base_x'][i];
            nodes.data['label_y'][i] = nodes.data['base_y'][i];
            nodes.data['text_angle'][i] = nodes.data['base_text_angle'][i];
            nodes.data['text_align'][i] = nodes.data['base_text_align'][i];
          }
          nodes.change.emit();

          // RESET LINKS
          var l_len = links.data['source_name'].length;
          for (var k = 0; k < l_len; k++) {
            links.data['line_alpha'][k] = 0.4;
            links.data['line_width'][k] = 1;
            links.data['color'][k] = '#666666';
          }
          links.change.emit();
        }
      }
    });
  </script>
  """
  html_content = html_content[:body_idx] + insert_html + resize_script + html_content[body_idx:]

extra_css = """
<style>
  html, body {
    height: 100%;
    width: 100%;
    margin: 0;
    padding: 0;
    background-color: #101010;
    overflow: hidden;
    display: flex;
    flex-direction: column; 
  }
  
  .bk-root {
    order: 1;
    width: 100% !important;
    height: 75vh !important; 
    min-height: 75vh !important;
    max-height: 75vh !important;
    display: flex;
    justify-content: center;
    align-items: center;
    position: relative; 
  }
  
  #details-panel {
    order: 2;
    width: 100%;
    height: 25vh; 
    flex: 0 0 25vh;
    background-color: #1a1a1a; 
    border-top: 1px solid #333;
    overflow-x: auto; 
    overflow-y: hidden;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
  }

  @media (min-aspect-ratio: 14/10) {
    body {
      flex-direction: row; 
    }
    .bk-root {
      width: auto !important;
      height: 100% !important;
      min-height: 100% !important;
      max-height: 100% !important;
      flex-grow: 1;
      order: 1;
    }
    #details-panel {
      flex: 0 0 25%; 
      width: 25%;
      height: 100%;
      border-top: none;
      border-left: 1px solid #333;
      order: 2;
      align-items: flex-start; 
      padding-left: 20px;
      padding-top: 20px;
      justify-content: flex-start;
      overflow-y: auto;
      overflow-x: hidden;
    }
  }
</style>
"""

html_content = html_content.replace('</head>', f'{extra_css}</head>')

with open(VIS_FILE_PATH, 'w', encoding='utf-8') as f:
  f.write(html_content)

print(f"Done. Saved to {VIS_FILE}")