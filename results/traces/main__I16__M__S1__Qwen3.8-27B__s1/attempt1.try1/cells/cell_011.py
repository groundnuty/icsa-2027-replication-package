import numpy as np, time
B = np.load("/tmp/B.npy"); Xall = np.load("/tmp/Xall.npy")
X_b = Xall[:4028].astype(np.float64)  # (4028, 60, 60)
Nc = 3600

t0=time.time()
thr = np.full((366, Nc), np.nan)
clm = np.full((366, Nc), np.nan)
for r in range(366):
    if r == 59:  # day 60: no pool
        continue
    P = X_b[B[r], :].T            # (3600, 121)
    S = np.sort(P, axis=1)        # NaNs sort last
    n = np.isfinite(P).sum(axis=1)
    # ---- hazen quantile (type 5): h = 1 + (n-1)*p ----
    ok = n > 0
    h = 1 + 0.9*(n[ok]-1)
    i = np.floor(h)
    g = h - i
    i0 = np.clip(i-1, 0, n[ok]-1)          # 0-based lower index
    lo = S[ok, i0.astype(int)]
    hi = np.where(i0+1 < n[ok], S[ok, (i0+1).astype(int)], lo)
    thr[r, ok] = (1-g)*lo + g*hi
    # ---- mean ----
    s = np.where(np.isfinite(P), P, 0.0).sum(axis=1)
    clm[r, ok] = s[ok]/n[ok]
print("loop done", time.time()-t0)

# day 60 = mean of 59 and 61
thr[59] = 0.5*(thr[58]+thr[60]); clm[59] = 0.5*(clm[58]+clm[60])
print("day60 finite:", np.isfinite(thr[59]).mean(), np.isfinite(clm[59]).mean())
print("any NaN rows:", [r for r in range(366) if not np.all(np.isfinite(thr[r]))], [r for r in range(366) if not np.all(np.isfinite(clm[r]))])

# ---- smoothing: 31-day centred, wrap over 366 ----
def smooth31(a):
    idx = (np.arange(366)[:,None] - 15 + np.arange(31)[None,:]) % 366
    return a[idx].mean(axis=1)
thr_s = smooth31(thr); clm_s = smooth31(clm)
print("smoothed finite:", np.isfinite(thr_s).all(), np.isfinite(clm_s).all())

# ---- verify hazen formula vs numpy for random pools ----
rng = np.random.default_rng(0)
bad = 0
for trial in range(40):
    r = int(rng.integers(0,366)); r = r if r<59 else r+1
    c = int(rng.integers(0,Nc))
    P = X_b[B[r], :][:, c]
    P = P[np.isfinite(P)]
    mine = thr[r, c]
    ref = np.quantile(P, 0.9, method="hazen") if len(P)>0 else np.nan
    if not (np.isnan(mine) and np.isnan(ref)) and not np.isclose(mine, ref, rtol=1e-12, atol=1e-9):
        bad += 1
print("hazen mismatches:", bad)
np.save("/tmp/thr_s.npy", thr_s); np.save("/tmp/clm_s.npy", clm_s)
np.save("/tmp/thr.npy", thr); np.save("/tmp/clm.npy", clm)
print("sample thresholds (cell0):", thr_s[152,0], thr_s[243,0], "clim", clm_s[152,0])
