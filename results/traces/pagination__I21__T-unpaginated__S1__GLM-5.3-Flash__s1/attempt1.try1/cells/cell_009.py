import os, numpy as np
print("tgt exists:", os.path.exists('/tmp/tgt.npy'))
if os.path.exists('/tmp/tgt.npy'):
    a = np.load('/tmp/tgt.npy')
    print("shape", a.shape, a.dtype, "sample mean", np.nanmean(a))
