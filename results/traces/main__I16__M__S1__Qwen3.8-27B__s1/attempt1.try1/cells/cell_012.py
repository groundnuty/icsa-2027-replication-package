import numpy as np, time
B = np.load("/tmp/B.npy"); Xall = np.load("/tmp/Xall.npy")
X_b = Xall[:4028].reshape(4028, 3600).astype(np.float64)
X_t = Xall[4028:].reshape(92, 3600).astype(np.float64)
Nc = 3600

t0=time.time()
thr = np.full((366, Nc), np.nan)
clm = np.full((366, Nc), np.nan)
for r in range(366):
    if r == 59:
        continue
    P = X_b[B[r]].T              # (3600, 121)
    S = np.sort(P, axis=1)       # NaNs last
    n = np.isfinite(P).sum(axis=1)
    ok = n > 0
    h = 1 + 0.9*(n[ok]-1)
    i = np.floor(h); g = h - i
    i0 = np.clip(i-1, 0, n[ok]-1).astype(int)
    lo = S[ok, i0]
    hi = np.where(i0+1 < n[ok], S[ok, i0+1], lo)
    thr[r, ok] = (1-g)*lo + g*hi
    s = np.where(np.isfinite(P), P, 0.0).sum(axis=1)
    clm[r, ok] = s[ok]/n[ok]
print("loop done", round(time.time()-t0,1), "s")

thr[59] = 0.5*(thr[58]+thr[60]); clm[59] = 0.5*(clm[58]+clm[60])
print("all finite thr/clm:", np.isfinite(thr).all(), np.isfinite(clm).all())

def smooth31(a):
    idx = (np.arange(366)[:,None] - 15 + np.arange(31)[None,:]) % 366
    return a[idx].mean(axis=1)
thr_s = smooth31(thr); clm_s = smooth31(clm)
print("smoothed finite:", np.isfinite(thr_s).all(), np.isfinite(clm_s).all())

rng = np.random.default_rng(0)
bad = 0
for trial in range(60):
    r = int(rng.integers(0,366)); r = r if r < 59 else r+1
    c = int(rng.integers(0,Nc))
    P = X_b[B[r], c]; P = P[np.isfinite(P)]
    ref = np.quantile(P, 0.9, method="hazen") if len(P)>0 else np.nan
    mine = thr[r, c]
    if not (np.isnan(mine) and np.isnan(ref)) and not np.isclose(mine, ref, rtol=1e-12, atol=1e-9):
        bad += 1
print("hazen mismatches vs numpy:", bad)

# independent date-based cross-check for a few (day, cell)
import datetime as dt
from datetime import date
def doy(d): return date(2000,d.month,d.day).toordinal()-date(2000,1,1).toordinal()+1
days_w = [date(1991,12,27)+dt.timedelta(i) for i in range(4028)]
valmap = {d: X_b[i] for i,d in enumerate(days_w)}
for (dd, cc) in [(1,0),(60,123),(200,456),(365,789),(59,0)]:
    r = dd-1
    pool=[]
    for y in range(1992,2003):
        for k in range(-5,6):
            u = date(y, *[ [1,2,3,4,5,6,7,8,9,10,11,12][0] ] )  # placeholder
    # proper: baseline dates with doy==dd
    bdates=[]
    for y in range(1992,2003):
        # find month/day of doy dd in leap cal
        ref = date(2000,1,1)+dt.timedelta(dd-1)
        try: t = date(y, ref.month, ref.day)
        except ValueError: continue
        bdates.append(t)
    vals=[]
    for t in bdates:
        for k in range(-5,6):
            u = t+dt.timedelta(k)
            if u in valmap:
                vals.append(valmap[u][cc])
    vals=[v for v in vals if np.isfinite(v)]
    refq = np.quantile(vals,0.9,method="hazen") if vals else np.nan
    refm = np.mean(vals) if vals else np.nan
    print(f"day{dd} cell{cc}: pool n={len(vals)} hazen {refq:.6f} vs thr {thr[r,cc]:.6f} | mean {refm:.6f} vs clm {clm[r,cc]:.6f}")
np.save("/tmp/thr.npy", thr); np.save("/tmp/clm.npy", clm)
np.save("/tmp/thr_s.npy", thr_s); np.save("/tmp/clm_s.npy", clm_s)
print("saved. sample thr_s day153/day244 cell0:", thr_s[152,0], thr_s[243,0])
