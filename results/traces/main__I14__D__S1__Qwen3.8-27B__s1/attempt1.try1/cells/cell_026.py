import numpy as np
thr = np.load('/work/data/thr_raw.npy').copy()
thr[59] = 0.5*(thr[58] + thr[60])
def circ31(A):
    A2 = np.concatenate([A[-15:], A, A[:15]], axis=0)
    W = np.lib.stride_tricks.sliding_window_view(A2, 31, axis=0)
    return W.mean(axis=2)
def circ31_naive(A, i):
    return np.mean([A[(i+k) % 366] for k in range(-15, 16)])
ts = circ31(thr)
nv = circ31_naive(thr, 0)
print("ts[0,0]  =", repr(ts[0,0]))
print("nv[0]    =", repr(nv[0]))
print("ts[0] dtype/shape:", ts.dtype, ts.shape)
print("nv dtype/shape:", nv.dtype, nv.shape)
print("ts[0,:5]:", ts[0,:5])
print("nv[:5]  :", nv[:5])
# manual mean of the window rows
A2 = np.concatenate([thr[-15:], thr, thr[:15]], axis=0)
print("A2[0:31,0].mean:", repr(np.mean(A2[0:31, 0])))
print("A2[0:31,0].sum/31:", repr(A2[0:31, 0].sum()/31))