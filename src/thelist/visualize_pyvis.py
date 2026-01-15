import pandas as pd
from pyvis.network import Network
import os

# 1. Load your Data
list_path = '/Volumes/Moana/Dropbox/inhumantouch.art/@importantstuff/theList'
data_path = 'data'
vis_path = 'visualizations'
csv_file = 'blend-data.csv'
csv_file_path = os.path.join(list_path, data_path, csv_file)# Make sure this matches your filename

if not os.path.exists(csv_file_path):
  print(f"Error: Could not find {csv_file_path}")
  exit()

df = pd.read_csv(csv_file_path)

# 2. Initialize the Graph
# height='100vh' means "Full Screen Height"
net = Network(height='100vh', width='100%', bgcolor='#222222', font_color='white', select_menu=True)

# 3. Add Nodes and Edges
# We iterate through the CSV and add connections
print(f"Processing {len(df)} connections...")
for index, row in df.iterrows():
  src = str(row['Source'])
  dst = str(row['Target'])
  
  # Add nodes (pyvis handles duplicates automatically)
  net.add_node(src, title=src, color='#00ff41') # Matrix Green dots
  net.add_node(dst, title=dst, color='#00ff41')
  
  # Add edge
  net.add_edge(src, dst, color='#555555')

# 4. Tune the Physics (The "Anti-Hairball" Settings)
# We set gravity low and spring length high to force them apart
net.set_options("""
var options = {
  "nodes": {
    "shape": "dot",
    "size": 10,
    "font": {
      "size": 14
    }
  },
  "edges": {
    "color": {
      "inherit": false
    },
    "smooth": false
  },
  "physics": {
    "barnesHut": {
      "gravitationalConstant": -80000,
      "centralGravity": 0.3,
      "springLength": 250,
      "springConstant": 0.04,
      "damping": 0.09,
      "avoidOverlap": 0.5
    },
    "minVelocity": 0.75
  }
}
""")

# 5. Generate and Open
vis_file = 'network_graph.html'
vis_file_path = os.path.join(list_path, vis_path, vis_file)
net.save_graph(vis_file)
print(f"Graph saved to {vis_file}. Opening now...")

# Try to open automatically (Mac/Windows/Linux compatible)
try:
    os.startfile(vis_file)
except AttributeError:
  # MacOS/Linux fallback
  import subprocess
  subprocess.call(['open', vis_file])