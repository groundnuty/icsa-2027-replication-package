import numpy as np, datetime
d = np.load("cache/region.npz")
st = np.load("cache/stage1.npz")
sst_b = d['sst_base']; tb = d['time_base']
thr_s, clim_s = st['thr_s'], st['clim_s']
nsea_all = st['nsea_all']
CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy(s): return CUM[int(s[5:7])-1] + int(s[8:10])
is_baseline = (tb >= "1992-01-01") & (tb <= "2002-12-31")
doy_b = np.array([doy(s) for s in tb], dtype=int)
base_dates = [datetime.date.fromisoformat(s) for s in tb]
base_pos = {day: np.where(is_baseline & (doy_b == day))[0] for day in range(1,367)}
D0 = datetime.date(1991,12,27)

sea_idx = np.argwhere(nsea_all.reshape(60,60))
rng = np.random.default_rng(42)
test_cells = rng.integers(0, len(sea_idx), 6)
WIN = {dd: [(dd-15+k) % 366 for k in range(31)] for dd in range(366)}
for tc in test_cells:
    la, lo = sea_idx[tc]
    col = sst_b[:, la, lo]
    raw_q = np.full(366, np.nan); raw_m = np.full(366, np.nan)
    for day in range(1, 367):
        if day == 60: continue
        pool = []
        for bi in base_pos[day]:
            bdate = base_dates[bi]
            for k in range(-5, 6):
                ti = int((bdate + datetime.timedelta(days=k) - D0).days)
                if 0 <= ti < len(col):
                    v = col[ti]
                    if np.isfinite(v):
                        pool.append(v)
        pool = np.array(pool)
        raw_q[day-1] = np.quantile(pool, 0.9, method='hazen') if pool.size else np.nan
        raw_m[day-1] = pool.mean() if pool.size else np.nan
    raw_q[59] = (raw_q[58] + raw_q[60]) / 2
    raw_m[59] = (raw_m[58] + raw_m[60]) / 2
    sm_q = np.array([raw_q[WIN[dd]].mean() for dd in range(366)])
    sm_m = np.array([raw_m[WIN[dd]].mean() for dd in range(366)])
    dq = np.abs(thr_s[:, tc] - sm_q).max(); dm = np.abs(clim_s[:, tc] - sm_m).max()
    print(f"cell {la:.2f},{lo:.2f}: thr diff {dq:.3e}  clim diff {dm:.3e}")