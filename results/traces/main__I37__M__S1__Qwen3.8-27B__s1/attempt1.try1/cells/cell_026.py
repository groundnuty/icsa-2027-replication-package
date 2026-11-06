import hashlib, numpy as np, os
rng = np.random.default_rng(7)
big = (rng.random((3000, 500), dtype=np.float32)).tobytes()  # 6MB... make it 60MB: 60*1024*1024
big = rng.random(int(60*1024*1024), dtype=np.uint8).tobytes()
ref = hashlib.sha256(big).hexdigest()
print("ref:", ref[:16])
for path in ('/tmp/mhw/big.bin', '/work/big.bin'):
    with open(path,'wb') as f:
        f.write(big)
    print(path, "written", os.path.getsize(path))
# also re-verify the small probes still ok
for path in ('/tmp/mhw/probe.npy', '/work/probe.npy'):
    h = hashlib.sha256(open(path,'rb').read()).hexdigest()[:16]
    print(path, h, "OK" if h.startswith('5fdef6b4600b0f6b') else "CORRUPT")
