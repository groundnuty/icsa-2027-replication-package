import numpy as np
z = np.load('/work/interim.npz')
sst_b = z['sst_b']
NC = 3600
origin = np.datetime64('1991-12-27','D')
def d2i(d64): return int((d64 - origin) // np.timedelta64(1,'D'))

def hazen90_cols(A):
    n = np.isfinite(A).sum(axis=0)
    S = np.sort(A, axis=0)
    out = np.full(A.shape[1], np.nan)
    ok = n > 0
    v = 0.9*n[ok] - 0.5
    vm = np.clip(v, 0.0, n[ok]-1)
    j = np.floor(vm).astype(np.int64)
    jj = np.clip(j+1, 0, n[ok]-1)
    g = vm - j
    cols = np.arange(n[ok].size)
    out[ok] = S[j, cols] + g*(S[jj, cols] - S[j, cols])
    return out, n

# d=153, good mapping (6,1)
d = 153
sl = []
for y in range(1992, 2003):
    bi = d2i(np.datetime64(f'{y:04d}-06-01','D'))
    sl.append(sst_b[bi-5:bi+6])
A = np.concatenate(sl, axis=0).reshape(121, NC)
print("A shape", A.shape, "finite counts min/max:", np.isfinite(A).sum(0).min(), np.isfinite(A).sum(0).max())
q, n = hazen90_cols(A)
print("cell5 q:", q[5], " n:", n[5])
print("q NaN count:", np.isnan(q).sum())
print("q[0:10]:", q[:10])
