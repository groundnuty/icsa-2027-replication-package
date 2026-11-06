import os, hashlib, numpy as np, time
p = '/tmp/mhw/sst_ext.npy'
def hashfile(p):
    h = hashlib.sha256()
    with open(p,'rb') as f:
        while True:
            b = f.read(1<<20)
            if not b: break
            h.update(b)
    return h.hexdigest()

st1 = os.stat(p)
h1 = hashfile(p)
with open(p,'rb') as f:
    head1 = f.read(32)
st2 = os.stat(p)
h2 = hashfile(p)
print("size:", st1.st_size, st2.st_size)
print("mtime:", st1.st_mtime, st2.st_mtime)
print("hash equal:", h1 == h2)
print("head1:", head1.hex())
time.sleep(2)
st3 = os.stat(p)
h3 = hashfile(p)
print("after sleep hash equal:", h3 == h1)
print("mtime3:", st3.st_mtime)
# also check mtime of other tmp files
for q in ('/tmp/mhw/sst_tgt.npy','/tmp/mhw/dates.pkl','/tmp/mhw/state.pkl'):
    s = os.stat(q)
    print(q, s.st_size, s.st_mtime)
