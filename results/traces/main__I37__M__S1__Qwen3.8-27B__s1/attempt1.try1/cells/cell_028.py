import hashlib, numpy as np
for path, prefix in (('/tmp/mhw/big.bin','4b1dc9ae94b0f846'), ('/work/big.bin','4b1dc9ae94b0f846')):
    h = hashlib.sha256(open(path,'rb').read()).hexdigest()[:16]
    print(path, h, "OK" if h == prefix else "CORRUPT")
# re-examine the sst files: are they corrupted again or recovered?
for path in ('/tmp/mhw/sst_ext.npy','/tmp/mhw/sst_tgt.npy'):
    with open(path,'rb') as f:
        head = f.read(8)
    print(path, "head:", head.hex())
