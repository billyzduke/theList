import pandas as pd
from pyvis.network import Network
import os

# 1. Load your Data
csv_file = 'blend-data.csv'  # Make sure this matches your filename
if not os.path.exists(csv_file):
  print(f"Error: Could not find {csv_file}")
  exit()

df = pd.read_csv(csv_file)

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
output_file = 'network_graph.html'
net.save_graph(output_file)
print(f"Graph saved to {output_file}. Opening now...")

# Try to open automatically (Mac/Windows/Linux compatible)
try:
    os.startfile(output_file)
except AttributeError:
  # MacOS/Linux fallback
  import subprocess
  subprocess.call(['open', output_file])