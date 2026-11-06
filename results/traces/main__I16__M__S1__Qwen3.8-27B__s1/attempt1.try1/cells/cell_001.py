import os
base = "/data/icsa2027_data_20261101T090944Z/s1z"
for root, dirs, files in os.walk(base):
    for f in files:
        p = os.path.join(root, f)
        print(p, os.path.getsize(p))
    # limit depth output
    if root.count(os.sep) > base.count(os.sep) + 2:
        dirs[:] = []
