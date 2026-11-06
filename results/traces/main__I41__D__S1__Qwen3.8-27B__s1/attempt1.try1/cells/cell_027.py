import numpy as np, pickle
from datetime import date, timedelta

thr = np.load('/work/thr_raw.npy'); thr_s = np.load('/work/thr_smooth.npy')
sea = np.load('/work/sea_mask.npy').ravel()

# window checks with equal_nan
manual0 = np.nanmean(np.concatenate([thr[351:366], thr[0:16]], axis=0), axis=0)
manual20 = np.nanmean(thr[5:36], axis=0)
print("day0 check (all):", np.allclose(thr_s[0], manual0, equal_nan=True))
print("day0 check (sea):", np.allclose(thr_s[0, sea], manual0[sea]))
print("day20 check (all):", np.allclose(thr_s[20], manual20, equal_nan=True))
print("day365 check (all):", np.allclose(thr_s[365], np.nanmean(np.concatenate([thr[350:366], thr[0:1]], axis=0), axis=0), equal_nan=True))

# day 60 pre-smooth check: thr[59] == mean(thr[58], thr[60]) for sea cells
print("day60 raw check (sea):", np.allclose(thr[59, sea], (thr[58, sea] + thr[60, sea]) / 2))

# ---- fully independent end-to-end reimplementation on random subset of sea cells ----
with open('/work/dates.pkl','rb') as f: dd = pickle.load(f)
base_dates, tgt_dates = dd['base'], dd['tgt']
nb = len(base_dates)
SST = np.load('/work/SST_all.npy')

doy_tab = {}
ref = date(2000,1,1)
for m in range(1,13):
    for day in range(1, 32):
        try:
            doy_tab[(m, day)] = (date(2000, m, day) - ref).days + 1
        except ValueError:
            pass

b_start, b_end = date(1992,1,1), date(2002,12,31)
idx_of = {d: i for i, d in enumerate(base_dates)}

def indep_thr(d, c):
    """independent: pool(d) = all SST(t) with t in window dates, exists b baseline, mdoy(b)=d, |t-b|<=5"""
    vals = []
    for i, t in enumerate(base_dates):
        hit = False
        b = t - timedelta(days=5)
        while b <= t + timedelta(days=5):
            if b_start <= b <= b_end and doy_tab[(b.month, b.day)] == d:
                hit = True; break
            b += timedelta(days=1)
        if hit:
            v = SST[i, c//60, c%60]
            if np.isfinite(v): vals.append(v)
    return np.quantile(np.array(vals), 0.9, method='hazen')

rng = np.random.default_rng(7)
idxs = rng.choice(np.where(sea)[0], size=40, replace=False)
ok = True
for c in idxs:
    for d in [1, 59, 61, 153, 244, 366]:
        a = thr[d-1, c]
        b = indep_thr(d, c)
        if not np.isclose(a, b, rtol=0, atol=1e-12):
            ok = False; print("MISMATCH cell", c, "day", d, a, b)
print("independent threshold cross-check (40 cells x 6 days):", "PASS" if ok else "FAIL")
