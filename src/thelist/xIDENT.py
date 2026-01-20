import sys
import bZdUtils

if __name__ == "__main__":
    # Check if the user actually provided a name
    if len(sys.argv) > 1:
        # sys.argv[1] is the first string passed after the filename
        target_name = sys.argv[1]
        xIDENT = bZdUtils.generate_xIDENT(target_name)
        print(f'{target_name} | {xIDENT}')
    else:
        print("Error: No name provided.")
        print("Usage: python xIDENT.py \"Miley Cyrus\"")