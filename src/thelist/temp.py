import os
import re
import csv

# --- CONFIGURATION ---
ROOT_DIR = '/Volumes/Moana/Dropbox/inhumantouch.art/'
OUTPUT_FILE = 'blend_names_taglines.csv'

# PASTE YOUR HEX CODES HERE
HEX_CODES_INPUT = """
000984
010ED1
01433E
019471
02C801
02E990
031FD3
04AFBA
052DC0
054717
059FBA
05DEE6
065AA9
07FFD8
0841AC
095DEE
0B044C
0B0959
0B0CB1
0B13DF
0B475A
0C3D63
0D1A55
0E8E37
0EA8BC
0F00F9
0FE162
101DF7
103F68
108806
10CDA3
111AEF
11310E
11CE2D
11D11E
11FC6E
12A065
12B9EB
13EDD5
14311B
14AE0D
14B95C
164419
1670E0
16A024
16DA12
173688
17DCCC
17ED16
18024B
1D569D
1DAEDE
1F0278
1F88B0
210AC9
222515
223749
2257D6
22BDAF
2358C8
237CF2
2397E2
23B32B
249802
249D64
257648
257D51
25AB93
26E696
272CFC
27F1B5
280618
28CFC0
29116E
294081
296262
2A0E68
2A70F5
2B1281
2BD570
2C23D8
2DDCA5
2DE5E2
2ECC68
30420E
3075E3
30C78E
30EBFF
3184B0
32B237
337D9D
33E99F
34C6CA
356B20
3696FE
37D411
381596
3A1F7D
3A84D8
3AEFE3
3AFF76
3B763E
3B7834
3BBA73
3BDEEE
3BEA29
3D5E9D
3DFDEB
3E4CED
3E97CD
3FAB16
4016B1
40D41C
411F07
4121DE
41904E
41A1CB
41C426
42F0A6
43074B
439D51
448D4A
46FA8A
475A7E
496F84
49E288
4A6B84
4A6CB9
4A9D70
4AE5E8
4BAB40
4BB2DB
4C0816
4C9880
4D1570
4D22C4
4DF530
4E8423
4EE936
502F89
506BEC
50B3D1
51A49A
523B14
53047A
53F7AA
543C5C
54B168
562B17
56EC67
583B19
59508A
59C2E0
59F233
5A091D
5A2721
5CAE82
5CD1A5
5D577D
5D7862
5DD0A3
5DE9B4
5FB242
62003A
63367B
63A8D5
63F697
64557E
649F67
6503BB
663336
66D180
670AD4
6B48CF
6F4007
6F5D3C
6FA177
6FA333
6FCD32
716A58
72E5B4
72F41E
7374EE
74D1C9
75CB13
78B550
798DCA
7A2828
7AD659
7BE0C3
7C2B47
7F6B0C
7FDE52
7FE2D8
8043BC
80E16E
817C00
822D29
827313
82C4A8
82F440
8369D4
837046
837932
83BC86
83D044
83FF07
849D9A
84A042
84CB85
851583
853203
8584A0
876972
8776D1
8828F4
885248
888399
88EB98
88F31E
89234C
89E3F1
8A9527
8B70E5
8E444B
8E866E
8F1C28
8F97E3
904577
9078BE
90958C
926862
927EA4
92946B
930148
939FA9
9481B2
94FD87
95124E
95ECE1
96794B
9708FB
9718BF
9872E1
99C8A5
9A4FEE
9ABCF6
9AD34F
9AE623
9B3AEC
9B489B
9BDE48
9C7DB6
9C82AF
9E0E22
9E6A29
9EE9D8
9F07EF
9F5171
9F59C1
9F5D04
9F698D
9FDA6C
A0A5E6
A14F59
A19DB1
A2AEFD
A388CE
A3E72B
A4BEC2
A4DBB0
A6062A
A641B1
A67A55
A6D459
A6FCC8
A8792F
A8F23C
A9A8B8
AA6B03
AA92AF
ACD522
ACE84D
AD9081
AE1B51
AF3292
B10ABF
B1C445
B20696
B207B1
B2C995
B3ED82
B40AF3
B4EFEB
B5859D
B591C3
B5C248
B73167
B82042
B88AF9
B8AEA3
BA3071
BADB11
BAEC8C
BB253C
BB6590
BBCB79
BCD07B
BE3EBF
BF4F4B
C1F41A
C2EB34
C3A78F
C3FCDB
C501FA
C5B3CB
C5E27C
C6291D
C6867C
C6D35D
C6EA86
C7401B
C77665
C7BD77
C85068
C8F172
C96951
CB9A8C
CBB53F
CC287F
CCEA53
CD5B66
CE0AEB
CE0EDD
CEE7FD
CF3789
D0D1F3
D0E7FC
D3A333
D405F1
D42240
D4B274
D593BD
D68D1A
D73FC2
D787D8
D820C0
D85815
D94690
D9ED0D
DA710F
DC56D6
DCCAB1
DDE53E
DE1596
DE3B08
DEB8AD
DEE31F
DF0F4A
DF9BB4
E0F16B
E2AEE1
E32B6D
E4AF36
E4BD25
E558D0
E6B1D8
E7110E
E773C1
E92C5B
E938C9
E99141
EA3189
EAF760
EC0F2B
EC301D
EC33A1
ECB986
ECF540
ED5194
EDAD5F
EE5A31
EEA12C
EF44A1
EF51E2
EFB01D
EFF55B
F02AFA
F0E303
F15704
F17099
F248E3
F273EF
F2B8FF
F2C189
F30DBB
F3A1FB
F4BABE
F546F5
F5A7E9
F64EE7
F6A7DE
F6FDCD
F707C2
F7D906
F95747
FA1F55
FC620E
FD318C
FD4A96
FD9AAD
FE5CE6
FEFE4F
FF1FAB
FF52C9
FFF9F9
"""

def extract_info_from_folder_string(folder_string):
    """
    Parses a single folder name string to find Name and Tagline.
    Returns (Name, Tagline) or (None, None).
    """
    name_part = ""
    
    # RULE A: The "=" Sign
    if "=" in folder_string:
        name_part = folder_string.split("=")[-1].strip()
        
    # RULE B: Single Word (No spaces)
    elif " " not in folder_string.strip():
        name_part = folder_string.strip()
        
    else:
        # Multiple words with no '=' usually means a date or generic folder
        return None, None

    # RULE C: Extract Tagline (Parentheses)
    tagline = ""
    tag_match = re.search(r'\((.*?)\)$', name_part)
    
    if tag_match:
        tagline = tag_match.group(1).strip()
        name_part = name_part.replace(f"({tagline})", "").replace("()", "").strip()

    return name_part, tagline

def get_target_folder_name(full_path):
    """
    Decides whether to look at the immediate parent or the grandparent
    based on the 'Trigger' rules.
    """
    parent_name = os.path.basename(full_path)
    
    # CONDITIONS TO GO UP A LEVEL:
    # 1. Contains "+" AND NOT "=" (e.g. "Miley+Dua")
    # 2. Contains "blendus" (case-insensitive)
    condition_1 = ('+' in parent_name) and ('=' not in parent_name)
    condition_2 = 'blendus' in parent_name.lower()
    
    if condition_1 or condition_2:
        # Go up to Grandparent
        grandparent_path = os.path.dirname(full_path)
        return os.path.basename(grandparent_path)
    
    # Otherwise, stay at Parent
    return parent_name

def main():
    # 1. Prepare Hex List
    target_hexes = set()
    for token in re.split(r'[,\s\n]+', HEX_CODES_INPUT):
        if token.strip():
            target_hexes.add(token.strip().upper())

    print(f"--- STARTING SCAN ---")
    print(f"Looking for {len(target_hexes)} hex codes in: {ROOT_DIR}")
    
    results = {}
    for h in target_hexes:
        results[h] = {'name': '', 'tagline': ''}

    found_count = 0

    # 2. Walk Directory
    for root, dirs, files in os.walk(ROOT_DIR):
        if found_count == len(target_hexes):
            break

        for filename in files:
            if filename.startswith('.'): continue

            # Extract Hex from Filename
            hex_match = re.search(r'(?<![A-Z0-9])([0-9A-F]{6})(?![A-Z0-9])', filename.upper())
            
            if hex_match:
                file_hex = hex_match.group(1)
                
                if file_hex in target_hexes:
                    # Check if we already have data for this hex
                    if results[file_hex]['name'] == '':
                        
                        # STEP 1: Determine WHICH folder to read (Parent vs Grandparent)
                        target_folder_string = get_target_folder_name(root)
                        
                        # STEP 2: Parse that folder string
                        name, tagline = extract_info_from_folder_string(target_folder_string)
                        
                        if name:
                            results[file_hex] = {'name': name, 'tagline': tagline}
                            print(f"[FOUND] {file_hex}: '{name}' (Tag: {tagline}) [Source: {target_folder_string}]")
                            found_count += 1

    # 3. Export
    print(f"-" * 60)
    print(f"Exporting to {OUTPUT_FILE}...")
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['hexcode', 'blend_name', 'blend_tagline'])
        for h in sorted(results.keys()):
            data = results[h]
            writer.writerow([h, data['name'], data['tagline']])

    print("Done!")

if __name__ == "__main__":
    main()