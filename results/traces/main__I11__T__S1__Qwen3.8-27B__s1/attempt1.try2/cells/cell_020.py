
import numpy as np, pickle, datetime as dt, warnings
warnings.filterwarnings("ignore")
dates = pickle.load(open("/work/dates.pkl","rb"))
base_days = dates["baseline_win"]; tgt_days = dates["target"]
Sb = np.load("/work/percell.npy")  # placeholder wrong; reload proper arrays below

# rebuild Sb/St same as compute
NC = 3600
Sb = np.empty((len(base_days), NC), np.float64)
for i, s in enumerate(base_days):
    Sb[i] = np.load(f"/work/reg/{s}.npy").ravel()
thr_s = np.load("/work/thr_s.npy"); clm_s = np.load("/work/clm_s.npy")
percell = np.load("/work/percell.npy")
doyT = np.load("/work/doyT.npy")
sea = np.isfinite(Sb[-92:]).all(axis=0) if False else None
St = np.empty((len(tgt_days), NC), np.float64)
for i, s in enumerate(tgt_days):
    St[i] = np.load(f"/work/reg/{s}.npy").ravel()
sea = np.isfinite(St).all(axis=0)

_leap0 = dt.date(2000,1,1)
def doy_of(s):
    y,m,d = map(int, s.split("-"))
    return (dt.date(2000,m,d) - _leap0).days + 1
doyB = np.array([doy_of(s) for s in base_days])
is_baseline = np.array([(s >= "1992-01-01") and (s <= "2002-12-31") for s in base_days])

# --- independent hazen quantile (manual) ---
def hazen90_manual(vals):
    v = np.sort(vals)
    n = len(v)
    h = (n + 1) * 0.9          # 1-based position
    lo = int(np.floor(h))
    frac = h - lo
    if lo < 1: return v[0]
    if lo >= n: return v[-1]
    return v[lo-1] + frac * (v[lo] - v[lo-1])

rng = np.random.default_rng(7)
sample_cells = rng.choice(np.where(sea)[0], 5, replace=False)
sample_doys = [153, 244, 61, 59, 200]
maxerr = 0.0
for c in sample_cells:
    for d in sample_doys:
        idxs = []
        for i, dv in enumerate(doyB):
            if dv == d and is_baseline[i]:
                idxs += list(range(i-5, i+6))
        vals = Sb[np.array(idxs), c]
        vals = vals[np.isfinite(vals)]
        expect = hazen90_manual(vals)
        got = thr_s[d-1, c]
        maxerr = max(maxerr, abs(expect - got))
print("threshold independent check max abs diff:", maxerr)
# also check a non-smoothed value: recompute one smoothed value by hand
c = sample_cells[0]; d = 153
A = np.load("/work/thr_s.npy")  # smoothed already; need unsmoothed -> recompute unsmoothed for this cell
idxs_all = {d2: [] for d2 in range(1,367)}
for i, dv in enumerate(doyB):
    if is_baseline[i]:
        for k in range(-5,6):
            idxs_all[dv].append(i+k)
unsm = np.full(366, np.nan)
for d2 in range(1,367):
    if d2 == 60: continue
    vals = Sb[np.array(idxs_all[d2]), c][np.isfinite(Sb[np.array(idxs_all[d2]), c])]
    unsm[d2-1] = hazen90_manual(vals)
unsm[59] = (unsm[58] + unsm[60]) / 2
def smooth_hand(arr, i0):
    tot = 0.0
    for k in range(-15, 16):
        tot += arr[((i0 + k) % 366)]
    return tot / 31
print("smooth independent check diff:", abs(smooth_hand(unsm, d-1) - A[d-1, c]))
