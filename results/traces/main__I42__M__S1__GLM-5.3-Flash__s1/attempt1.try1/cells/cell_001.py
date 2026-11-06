import os
base = "/data/icsa2027_data_20261101T090944Z/s1z"
for root, dirs, files in os.walk(base):
    print(root, "dirs:", dirs[:20], "nfiles:", len(files))
    for f in files[:10]:
        print("   ", f)
    if len(files) > 10:
        print("    ...")
