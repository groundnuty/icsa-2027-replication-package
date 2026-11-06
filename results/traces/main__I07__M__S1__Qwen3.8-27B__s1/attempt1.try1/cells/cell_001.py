import os
base = "/data/icsa2027_data_20261101T090944Z/s1z"
for root, dirs, files in os.walk(base):
    level = root.replace(base, "").count(os.sep)
    if level < 3:
        print("  "*level + os.path.basename(root) + "/")
        for f in files[:50]:
            sz = os.path.getsize(os.path.join(root, f))
            print("  "*(level+1) + f, sz)
