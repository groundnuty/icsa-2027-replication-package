import numpy as np
thr = np.load('/work/data/thr_raw.npy').copy()
clim = np.load('/work/data/clim_raw.npy').copy()
thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])

def circ31(A):
    A2 = np.concatenate([A[-15:], A, A[:15]], axis=0)
    W = np.lib.stride_tricks.sliding_window_view(A2, 31, axis=0)
    return W.mean(axis=2)
def circ31_naive(A, i):
    return np.mean([A[(i+k) % 366] for k in range(-15, 16)])

ts, cs = circ31(thr), circ31(clim)
for i in [0, 5, 58, 59, 60, 200, 364, 365]:
    dt = np.abs(ts[i] - circ31_naive(thr, i)).max()
    dc = np.abs(cs[i] - circ31_naive(clim, i)).max()
    print(i, "thr maxdiff", dt, "clim maxdiff", dc)