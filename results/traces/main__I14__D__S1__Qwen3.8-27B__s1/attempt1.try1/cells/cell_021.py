import numpy as np
thr = np.load('/work/data/thr_raw.npy')
clim = np.load('/work/data/clim_raw.npy')
thr[59] = 0.5*(thr[58] + thr[60])
def circ31(A):
    A2 = np.concatenate([A[-15:], A, A[:15]], axis=0)
    W = np.lib.stride_tricks.sliding_window_view(A2, 31, axis=0)
    return W.mean(axis=2)
def circ31_naive(A, i):
    return np.mean([A[(i+k) % 366] for k in range(-15, 16)])
ts = circ31(thr)
d0 = ts[0] - circ31_naive(thr, 0)
print("i=0 max diff:", np.abs(d0).max())
# check index alignment: which elements differ?
naive = circ31_naive(thr, 0)
vec = ts[0]
bad = np.flatnonzero(np.abs(d0) > 1e-9)
print("n bad:", len(bad))
if len(bad):
    c = bad[0]
    print("col", c, "vec", vec[c], "naive", naive[c])
    idxs = [(0+k) % 366 for k in range(-15, 16)]
    print("naive mean of", [thr[j, c] for j in idxs][:3], "...", np.mean([thr[j, c] for j in idxs]))
    print("window A2[0:31] corresponds to thr rows:", list(range(351,366)) + list(range(0,16)))