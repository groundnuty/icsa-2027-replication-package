import os, hashlib, numpy as np
print("output dir exists (created in earlier call):", os.path.isdir('/work/output'))
rng = np.random.default_rng(42)
blob = rng.random(1<<20, dtype=np.float64).tobytes()
for path in ('/tmp/mhw/probe.npy', '/work/probe.npy'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,'wb') as f:
        f.write(blob)
    h = hashlib.sha256(open(path,'rb').read()).hexdigest()
    print(path, "written, sha256:", h[:16], "size:", os.path.getsize(path))
h_ref = hashlib.sha256(blob).hexdigest()
print("reference:", h_ref[:16])
print("work usage:", os.statvfs('/work').f_bavail, "blocks avail")
