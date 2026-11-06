import numpy as np, datetime as dt
from datetime import date
B = np.load("/tmp/B.npy"); Xall = np.load("/tmp/Xall.npy")
X_b = Xall[:4028].reshape(4028, 3600)
X_t = Xall[4028:].reshape(92, 3600)
thr = np.load("/tmp/thr.npy")  # will re-save after this check

rng = np.random.default_rng(1)
bad=0; tested=0
for _ in range(300):
    r = int(rng.integers(0,366))
    if r == 59: continue
    c = int(rng.integers(0,3600))
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
ocean = np.load("/tmp/ocean.npy")
def smooth31(a):
    idx = (np.arange(366)[:,None] - 15 + np.arange(31)[None,:]) % 366
    return a[idx].mean(axis=1)
clm = np.load("/tmp/clm.npy")
thr_s = smooth31(thr); clm_s = smooth31(clm)
np.save("/tmp/thr_s.npy", thr_s); np.save("/tmp/clm_s.npy", clm_s)
print("smoothed saved; ocean:", int(ocean.sum()))
print("sample thr_s 153/244 cell0:", round(thr_s[152,0],4), round(thr_s[243,0],4))
