import numpy as np
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
    if d_ == 60:
        continue
    mask = np.zeros(N, dtype=bool)
    for i in np.where(is_baseline & (doy_b == d_))[0]:
        mask[max(i-5,0):min(i+5,N-1)+1] = True
    pool_idx.append((d_, np.flatnonzero(mask)))

sst_t = d['sst_tgt']
nsea_all = np.isfinite(sst_t).all(axis=0).reshape(-1)
nsea = int(nsea_all.sum())
S = sst_b.reshape(N, -1)[:, nsea_all]
print("S finite frac:", np.isfinite(S).mean(), S.shape)

d_, idx = pool_idx[0]
V = S[idx, :].T
print("V shape:", V.shape, "finite:", np.isfinite(V).sum())
fin = np.isfinite(V)
n = fin.sum(axis=1)
print("n[:5]:", n[:5])
W = np.sort(np.where(fin, V, np.inf), axis=1)
r = 0.9 * n - 0.5
f = np.clip(np.floor(r).astype(np.int64), 0, np.maximum(n-1, 0))
c = np.clip(np.ceil(r).astype(np.int64), 0, np.maximum(n-1, 0))
q = W[np.arange(nsea), f] + (r - f) * (W[np.arange(nsea), c] - W[np.arange(nsea), f])
print("q[:5]:", q[:5])
# cross-check one cell with np.quantile
xf = V[0][np.isfinite(V[0])]
print("np.quantile check:", np.quantile(xf, 0.9, method='hazen'), q[0])