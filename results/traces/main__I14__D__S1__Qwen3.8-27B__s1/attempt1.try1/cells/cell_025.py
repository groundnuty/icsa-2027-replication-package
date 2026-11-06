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
d = np.abs(ts[0] - nv)
print("max diff:", d.max())
bad = np.flatnonzero(d > 1e-9)
print("n bad:", len(bad), bad[:10])
if len(bad):
    c = bad[0]
    lst = [A if False else None]
    vals_list = [thr[(0+k) % 366, c] for k in range(-15, 16)]
    A2 = np.concatenate([thr[-15:], thr, thr[:15]], axis=0)
    print("list values:", np.round(vals_list, 4))
    print("vec  values:", np.round(A2[0:31, c], 4))
    print("list mean:", np.mean(vals_list), "vec mean:", np.mean(A2[0:31, c]))
    print("list elementwise equal:", np.array_equal(np.array(vals_list), A2[0:31, c]))