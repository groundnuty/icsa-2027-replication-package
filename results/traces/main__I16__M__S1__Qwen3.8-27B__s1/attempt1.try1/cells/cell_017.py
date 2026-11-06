import numpy as np, time, datetime as dt
from datetime import date
B = np.load("/tmp/B.npy"); Xall = np.load("/tmp/Xall.npy")
X_b = Xall[:4028].reshape(4028, 3600)
X_t = Xall[4028:].reshape(92, 3600)
Nc = 3600
t0=time.time()
thr = np.full((366, Nc), np.nan); clm = np.full((366, Nc), np.nan)
nnz = np.zeros((366, Nc))
for r in range(366):
    if r == 59: continue
    P = X_b[B[r]].T
    S = np.sort(P, axis=1)
    n = np.isfinite(P).sum(axis=1)
    ok = n > 0
    h = n[ok]*0.9 + 0.5
    i = np.floor(h); g = h - i
    i0 = np.clip(i-1, 0, n[ok]-1).astype(int)
    lo = S[ok, i0]
    hi = np.where(i0+1 < n[ok], S[ok, i0+1], lo)
    thr[r, ok] = (1-g)*lo + g*hi
    s = np.where(np.isfinite(P), P, 0.0).sum(axis=1)
    clm[r, ok] = s[ok]/n[ok]
    nnz[r, ok] = n[ok]
thr[59] = 0.5*(thr[58]+thr[60]); clm[59] = 0.5*(clm[58]+clm[60]); nnz[59] = 1
print("loop", round(time.time()-t0,1), "s")

ocean = np.isfinite(X_t).all(axis=0)
np.save("/tmp/ocean.npy", ocean)
print("ocean cells:", int(ocean.sum()))
print("min pool size among ocean cells:", int(nnz[:, ocean].min()))
print("thr finite on ocean:", bool(np.isfinite(thr[:, ocean]).all()), "clm:", bool(np.isfinite(clm[:, ocean]).all()))

rng = np.random.default_rng(1)
bad=0; tested=0
for _ in range(300):
    r = int(rng.integers(0,366))
    if r == 59: continue
    c = int(rng.integers(0,Nc))
    P = X_b[B[r], c]; P = P[np.isfinite(P)]
    ref = np.quantile(P,0.9,method="hazen") if len(P) else np.nan
    mine = thr[r,c]
    tested+=1
    if not (np.isnan(mine)==np.isnan(ref)) or (len(P) and not np.isclose(mine,ref,rtol=1e-12,atol=1e-9)): bad+=1
print("hazen mismatches:", bad, "/", tested)

def doy(d): return date(2000,d.month,d.day).toordinal()-date(2000,1,1).toordinal()+1
days_w = [date(1991,12,27)+dt.timedelta(i) for i in range(4028)]
valmap = {d: X_b[i] for i,d in enumerate(days_w)}
def ref_pool(dd, cc):
    refmd = date(2000,1,1)+dt.timedelta(dd-1)
    vals=[]
    for y in range(1992,2003):
        try: t = date(y, refmd.month, refmd.day)
        except ValueError: continue
        for k in range(-5,6):
            u = t+dt.timedelta(k)
            v = valmap.get(u)
            if v is not None:
                vals.append(v[cc])
    return [v for v in vals if np.isfinite(v)]
for dd, cc in [(1,0),(60,123),(200,456),(365,789),(153,1000),(59,1800)]:
    vals = ref_pool(dd, cc)
    refq = np.quantile(vals,0.9,method="hazen") if vals else float('nan')
    refm = float(np.mean(vals)) if vals else float('nan')
    print(f"day{dd} cell{cc} n={len(vals)}: hazen {refq:.5f} vs {thr[dd-1,cc]:.5f} | mean {refm:.5f} vs {clm[dd-1,cc]:.5f}")

def smooth31(a):
    idx = (np.arange(366)[:,None] - 15 + np.arange(31)[None,:]) % 366
    return a[idx].mean(axis=1)
thr_s = smooth31(thr); clm_s = smooth31(clm)
np.save("/tmp/thr.npy", thr); np.save("/tmp/clm.npy", clm)
np.save("/tmp/thr_s.npy", thr_s); np.save("/tmp/clm_s.npy", clm_s)
print("saved. sample thr_s day153/day244 cell0:", round(float(thr_s[152,0]),4), round(float(thr_s[243,0]),4))
# smoothing sanity: constant array unchanged
const = smooth31(np.full((366,1),3.0)); print("smooth const:", const[0,0])
