
import os, struct
local_dir = '/work/files'
files = sorted(os.listdir(local_dir))
print("count:", len(files))
sizes = {}
bad = []
for f in files:
    p = os.path.join(local_dir, f)
    s = os.path.getsize(p)
    sizes[s] = sizes.get(s, 0) + 1
    with open(p, 'rb') as fh:
        head = fh.read(4)
        if head != b'\x89HDF':
            bad.append((f, s))
print("bad HDF5 headers:", bad[:10], "n bad:", len(bad))
print("distinct sizes:", len(sizes))
import statistics
ss = list(sizes.values())
print("min/max size files:", min(sizes), max(sizes))
