import numpy as np, datetime
d = np.load("cache/region.npz")
st = np.load("cache/stage1.npz")
sst_b = d['sst_base']; sst_t = d['sst_tgt']; tb = d['time_base']; tt = d['time_tgt']
thr_s, clim_s = st['thr_s'], st['clim_s']
nsea_all = st['nsea_all']; hot = st['hot']; mhw = st['mhw']
CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy(s): return CUM[int(s[5:7])-1] + int(s[8:10])
is_baseline = (tb >= "1992-01-01") & (tb <= "2002-12-31")
doy_b = np.array([doy(s) for s in tb], dtype=int)
sea_idx = np.argwhere(nsea_all.reshape(60,60))

rng = np.random.default_rng(42)
test_cells = rng.integers(0, len(sea_idx), 6)
days_test = [1, 59, 60, 61, 152, 153, 244, 365, 366, 200]

base_dates = [datetime.date.fromisoformat(s) for s in tb]
for tc in test_cells:
    la, lo = sea_idx[tc]
    col = sst_b[:, la, lo]
    for day in days_test:
        # literal pool construction
        pool = []
        for bi, bdate in enumerate(base_dates):
            if not is_baseline[bi] or doy_b[bi] != day:
                continue
            for k in range(-5, 6):
                t = bdate + datetime.timedelta(days=k)
                ti = int((datetime.date.fromisoformat(t.isoformat()) - datetime.date(1991,12,27)).days)
                if 0 <= ti < len(col):
                    v = col[ti]
                    if np.isfinite(v):
                        pool.append(v)
        pool = np.array(pool)
        if day == 60:
            continue
        q = np.quantile(pool, 0.9, method='hazen')
        m = pool.mean()
        # reconstruct smoothed version: need raw for neighbours... do it for all 366 days for this cell
    # do full raw arrays for this cell and compare smoothing
    raw_q = np.full(366, np.nan); raw_m = np.full(366, np.nan)
    for day in range(1, 367):
        if day == 60: continue
        pool = []
        for bi in np.where(is_baseline & (doy_b == day))[0]:
            bdate = base_dates[bi]
            for k in range(-5, 6):
                t = bdate + datetime.timedelta(days=k)
                ti = int((t - datetime.date(1991,12,27)).days)
                if 0 <= ti < len(col):
                    v = col[ti]
                    if np.isfinite(v):
                        pool.append(v)
        pool = np.array(pool)
        raw_q[day-1] = np.quantile(pool, 0.9, method='hazen') if pool.size else np.nan
        raw_m[day-1] = pool.mean() if pool.size else np.nan
    raw_q[59] = (raw_q[58] + raw_q[60]) / 2
    raw_m[59] = (raw_m[58] + raw_m[60]) / 2
    sm_q = np.array([raw_q[(day-15+k) % 366 for k in range(31)].mean() for day in range(1, 367)])
    sm_m = np.array([raw_m[(day-15+k) % 366 for k in range(31)].mean() for day in range(1, 367)])
    ci = tc  # column in sea-ordered arrays == order of sea_idx
    print(f"cell {la},{lo}: thr max abs diff {np.abs(thr_s[:,ci]-sm_q).max():.3e}  clim max abs diff {np.abs(clim_s[:,ci]-sm_m).max():.3e}")