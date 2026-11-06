
import numpy as np, pickle, datetime as dt, warnings
warnings.filterwarnings("ignore")
dates = pickle.load(open("/work/dates.pkl","rb"))
base_days = dates["baseline_win"]
NC=3600
Sb = np.empty((len(base_days), NC), np.float64)
for i, s in enumerate(base_days):
    Sb[i] = np.load(f"/work/reg/{s}.npy").ravel()
thr_s = np.load("/work/thr_s.npy")
_leap0 = dt.date(2000,1,1)
def doy_of(s):
    y,m,d = map(int, s.split("-"))
    return (dt.date(2000,m,d) - _leap0).days + 1
doyB = np.array([doy_of(s) for s in base_days])
is_baseline = np.array([(s >= "1992-01-01") and (s <= "2002-12-31") for s in base_days])

def hazen90_manual(vals):
    v = np.sort(vals); n = len(v); h = (n+1)*0.9
    lo = int(np.floor(h)); frac = h-lo
    if lo < 1: return v[0]
    if lo >= n: return v[-1]
    return v[lo-1] + frac*(v[lo]-v[lo-1])

c = 12345 % 3600
# recompute pipeline unsmoothed for this cell exactly as in compute.py
idx = {s: i for i,s in enumerate(base_days)}
pools = {}
for d in range(1,367):
    if d == 60: continue
    idxs = set()
    for i, dv in enumerate(doyB):
        if dv == d and is_baseline[i]:
            for k in range(-5,6): idxs.add(i+k)
    pools[d] = np.sort(np.array(sorted(idxs)))
unsm_pipe = np.full(366, np.nan)
for d in range(1,367):
    if d == 60: continue
    X = Sb[pools[d], c]
    unsm_pipe[d-1] = np.nanquantile(X, 0.90, method="hazen")
unsm_pipe[59] = (unsm_pipe[58]+unsm_pipe[60])/2
# manual
unsm_man = np.full(366, np.nan)
for d in range(1,367):
    if d == 60: continue
    vals = Sb[pools[d], c][np.isfinite(Sb[pools[d], c])]
    unsm_man[d-1] = hazen90_manual(vals)
unsm_man[59] = (unsm_man[58]+unsm_man[60])/2
diff = np.abs(unsm_pipe - unsm_man)
print("max unsmoothed diff pipe vs manual:", diff.max(), "at doy", diff.argmax()+1)
# compare smoothing
def smooth366(A):
    ext = np.concatenate([A,A], axis=0)
    out = np.empty_like(A)
    for i in range(366):
        s = (i-15)%366
        out[i] = ext[s:s+31].mean(axis=0)
    return out
sm_pipe = smooth366(unsm_pipe)
print("smooth of pipe unsmoothed vs stored thr_s, max diff:", np.abs(sm_pipe - thr_s).max())
