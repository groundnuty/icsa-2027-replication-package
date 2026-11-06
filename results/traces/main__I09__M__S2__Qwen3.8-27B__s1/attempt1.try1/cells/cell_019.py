import numpy as np
# rebuild quickly (stage1 didn't save because of the bad assert)
d = np.load("cache/region.npz")
sst_b = d['sst_base']; tb = d['time_base']
CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy(s):
    return CUM[int(s[5:7])-1] + int(s[8:10])
doy_b = np.array([doy(s) for s in tb], dtype=int)
is_baseline = (tb >= "1992-01-01") & (tb <= "2002-12-31")
N = len(tb)
pool_idx = []
for d_ in range(1, 367):
    if d_ == 60: continue
    mask = np.zeros(N, dtype=bool)
    for i in np.where(is_baseline & (doy_b == d_))[0]:
        mask[max(i-5,0):min(i+5,N-1)+1] = True
    pool_idx.append((d_, np.flatnonzero(mask)))
nsea_all = np.isfinite(d['sst_tgt']).all(axis=0).reshape(-1)
nsea = int(nsea_all.sum())
S = sst_b.reshape(N, -1)[:, nsea_all]
thr = np.full((366, nsea), np.nan); arow = np.arange(nsea)
for d_, idx in pool_idx:
    V = S[idx, :].T
    fin = np.isfinite(V); n = fin.sum(axis=1)
    W = np.sort(np.where(fin, V, np.inf), axis=1)
    r = 0.9*n - 0.5
    f = np.clip(np.floor(r).astype(np.int64), 0, np.maximum(n-1,0))
    c = np.clip(np.ceil(r).astype(np.int64), 0, np.maximum(n-1,0))
    q = W[arow,f] + (r-f)*(W[arow,c]-W[arow,f]); q[n==0] = np.nan
    thr[d_-1,:] = q
thr[59,:] = (thr[58,:]+thr[60,:])/2.0
I = np.mod(np.arange(366)[:,None] - 15 + np.arange(31)[None,:], 366)
thr_s = thr[I, :].mean(axis=1)

# verify every day of every cell against direct windowed mean (one cell, all 366 days)
cell = 123
ok = True
for d0 in range(366):
    w = [(d0 - 15 + k) % 366 for k in range(31)]
    ref = thr[w, cell].mean()
    if not np.isclose(thr_s[d0, cell], ref):
        ok = False; print("mismatch at", d0); break
print("per-day window check:", "PASS" if ok else "FAIL")
# also verify wrap window for day 0 contains 365,364,0..15
print("day0 window:", I[0].tolist())