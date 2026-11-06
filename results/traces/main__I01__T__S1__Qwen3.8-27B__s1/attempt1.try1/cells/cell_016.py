
import os, h5py
local_dir = '/work/files'
files = sorted(os.listdir(local_dir))
bad = []
good = 0
for i, f in enumerate(files):
    p = os.path.join(local_dir, f)
    s = os.path.getsize(p)
    ok = False
    if s > 100:
        with open(p, 'rb') as fh:
            magic = fh.read(8)
        if magic == b'\x89HDF\r\n\x1a\n':
            try:
                with h5py.File(p, 'r') as hf:
                    # force reading of root attributes to ensure structure readable
                    _ = list(hf.keys())
                    ok = True
            except Exception:
                ok = False
    if ok:
        good += 1
    else:
        bad.append((f, s))
        os.remove(p)
print("good:", good, "removed bad:", len(bad))
print("removed examples:", bad[:5])
print("remaining:", len(os.listdir(local_dir)))
print("free:", os.statvfs('/work').f_bavail * os.statvfs('/work').f_bsize / 1e6, "MB")
