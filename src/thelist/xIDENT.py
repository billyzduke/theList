from util import generate_xIDENT, get_first_pos_arg 

if __name__ == "__main__":
  # Check if the user actually provided a name
  name = get_first_pos_arg()
  
  if name:
    print(f"Generating ID for: {name}")
    xIDENT = generate_xIDENT(name)
    print(f'{name} | {xIDENT}')
  else:
    print("Error: No name provided.")
    print("Usage: python xIDENT.py \"Miley Cyrus\"")
