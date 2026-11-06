
import numpy as np, datetime, fsspec, xarray as xr, time

# --- 1) full per-day hot counts with correct doy mapping
thr_s = np.load('work/thr_smooth.npy')
S_tgt = np.load('work/S_tgt.npy')
N = 3600; T = 92
sea = np.load('work/sea.npy')
t0 = datetime.date(2017,6,1)
tgt_dates = [t0 + datetime.timedelta(days=i) for i in range(T)]
dbm = {1:0, 2:31, 3:60, 4:91, 5:121, 6:152, 7:182, 8:213, 9:244, 10:274, 11:305, 12:335}
doy_t = np.array([dbm[d.month] + d.day for d in tgt_dates])
S64 = S_tgt.astype(np.float64).reshape(T, N)
H = (S64 >= thr_s[doy_t]) & sea[None, :]
hpd = H.sum(axis=1)
hot_days = [(str(tgt_dates[i]), int(hpd[i])) for i in range(T) if hpd[i] > 0]
print("days with any hot cell:", len(hot_days))
for x in hot_days: print("  ", x)
np.save('work/H2.npy', H)

# --- 2) independent slow threshold check for 3 random sea cells
S_base = np.load('work/S_base.npy')
base_dates = [datetime.date(1992,1,1) + datetime.timedelta(days=i) for i in range(4018)]
win_dates = [datetime.date(1991,12,27) + datetime.timedelta(days=i) for i in range(4028)]
date2idx = {d: i for i, d in enumerate(win_dates)}
def slow_pool(cell, doyear):
    vals = []
    for j, b in enumerate(base_dates):
        mo, da = b.month, b.day
        bdoy = dbm[mo] + da
        if bdoy == doyear:
            for k in range(-5, 6):
                t = b + datetime.timedelta(days=k)
                v = S_base[date2idx[t], cell[0], cell[1]]
                vals.append(v)
    return np.array(vals, dtype=np.float64)
def hazen_q(x, p=0.9):
    x = x[~np.isnan(x)]; x = np.sort(x); n = x.size
    h = (n + 1) * p - 1
    lo = int(np.floor(h)); hi = min(lo + 1, n - 1)
    return x[lo] + (h - lo) * (x[hi] - x[lo])
cs = np.where(sea)[0]
rng = np.random.default_rng(0)
picks = rng.choice(cs, 5, replace=False)
for c in picks:
    ci = np.unravel_index(int(c), (60,60))
    for doy in (153, 197, 213):
        X = slow_pool(ci, doy)
        q_slow = hazen_q(X); m_slow = np.nanmean(X)
        q_fast = np.nanquantile(X, 0.9, method='hazen')
        assert abs(q_slow - q_fast) < 1e-12, (c, doy, q_slow, q_fast)
        # raw (unsmoothed) value from our pipeline
        print(f"cell {ci} doy {doy}: pool n={len(X)}, thr_raw={thr_raw[doY-1 if False else doy-1, c]:.4f} slow={q_slow:.4f} clim_raw={clim_raw[doy-1,c]:.4f} slow_mean={m_slow:.4f}")
print("slow/fast quantile agree")
