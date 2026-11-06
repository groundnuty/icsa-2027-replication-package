
import numpy as np, pickle, datetime as dt, warnings
warnings.filterwarnings("ignore")
dates = pickle.load(open("/work/dates.pkl","rb"))
base_days = dates["baseline_win"]
NC=3600
Sb = np.empty((len(base_days), NC), np.float64)
for i, s in enumerate(base_days):
    Sb[i] = np.load(f"/work/reg/{s}.npy").ravel()
thr_s = np.load("/work/thr_s.npy"); clm_s = np.load("/work/clm_s.npy")
_leap0 = dt.date(2000,1,1)
def doy_of(s):
    y,m,d = map(int, s.split("-"))
    return (dt.date(2000,m,d) - _leap0).days + 1
doyB = np.array([doy_of(s) for s in base_days])
is_baseline = np.array([(s >= "1992-01-01") and (s <= "2002-12-31") for s in base_days])

def hazen90(vals):  # HF type 5 / Hazen: 1-based h = n*p + 0.5
    v = np.sort(vals); n = len(v); h = n*0.9 + 0.5
    lo = int(np.floor(h)); frac = h-lo
    if lo < 1: return v[0]
    if lo > n: return v[-1]
    if lo == n and frac == 0: return v[-1]
    return v[lo-1] + frac*(v[lo]-v[lo-1]) if lo < n else v[-1]

def smooth366(A):
    ext = np.concatenate([A,A], axis=0)
    out = np.empty_like(A)
    for i in range(366):
        s=(i-15)%366; out[i]=ext[s:s+31].mean(axis=0)
    return out

rng = np.random.default_rng(11)
St = np.load("/work/percell.npy")  # wrong file; reload target
tgt = dates["target"]
St = np.empty((len(tgt), NC), np.float64)
for i, s in enumerate(tgt):
    St[i] = np.load(f"/work/reg/{s}.npy").ravel()
sea = np.isfinite(St).all(axis=0)
cells = rng.choice(np.where(sea)[0], 8, replace=False)
doys  = [1, 59, 61, 153, 200, 244, 366, 300]
maxerr_thr = maxerr_clm = 0.0
for c in cells:
    unsm = np.full(366, np.nan); uncl = np.full(366, np.nan)
    for d in range(1,367):
        if d == 60: continue
        idxs = set()
        for i, dv in enumerate(doyB):
            if dv == d and is_baseline[i]:
                idxs.update(range(i-5, i+6))
        vals = Sb[np.array(sorted(idxs)), c]
        fv = vals[np.isfinite(vals)]
        unsm[d-1] = hazen90(fv)
        uncl[d-1] = fv.mean()
    unsm[59] = (unsm[58]+unsm[60])/2; uncl[59] = (uncl[58]+uncl[60])/2
    maxerr_thr = max(maxerr_thr, np.abs(smooth366(unsm) - thr_s[:, c]).max())
    maxerr_clm = max(maxerr_clm, np.abs(smooth366(uncl) - clm_s[:, c]).max())
print("independent verification max abs diff — threshold:", maxerr_thr, "climatology:", maxerr_clm)
