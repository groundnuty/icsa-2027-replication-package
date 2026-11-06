import numpy as np, datetime as dt

z = np.load('mhw_cache.npz', allow_pickle=False)
base_data = z['base_data']; tgt_data = z['tgt_data']
c = np.load('clim_thr.npz'); thr_s = c['thr']; clm_s = c['clm']

def doy366(d):
    cum = [0,31,59,90,120,151,181,212,243,273,304,334]
    if d.month==2 and d.day==29: return 60
    v = cum[d.month-1]+d.day
    return v+1 if d.month>=3 else v

ext_days = [dt.date(1991,12,27)+dt.timedelta(days=k) for k in range(base_data.shape[0])]

# find a hot cell on 2004-08-01 (k=61)
d0 = dt.date(2004,8,1); k0 = (d0-dt.date(2004,6,1)).days
diff0 = tgt_data[k0] - thr_s[doy366(d0)-1]
i,j = np.unravel_index(np.nanargmax(diff0), diff0.shape)
print(f"hottest cell on 2004-08-01: ({i},{j}) SST={tgt_data[k0,i,j]:.3f} thr={thr_s[doy366(d0)-1,i,j]:.4f} diff={diff0[i,j]:+.4f}")

# hand-check: raw p90 per doy 199..229, then 31-day mean
def raw_p90(dd):
    d = doy366(dd)
    if d == 60: return None
    pool = []
    for m, ed in enumerate(ext_days):
        y = ed.year
        if not (1992 <= y <= 2002): continue
        if doy366(ed) == d:
            pool.append(base_data[m-5:m+6, i, j])
    pool = np.concatenate(pool).astype(np.float64)
    return np.nanpercentile(pool, 90, method='hazen')

vals = []
for off in range(-15, 16):
    dd = d0 + dt.timedelta(days=off)
    p = raw_p90(dd)
    if p is None:
        # day 60 -> mean of days 59 and 61
        p = 0.5*(raw_p90(dd - dt.timedelta(days=1)) + raw_p90(dd + dt.timedelta(days=1)))
    vals.append(p)
hand = float(np.mean(vals))
print("hand smoothed thr:", hand, "| vectorized thr:", thr_s[doy366(d0)-1,i,j], "| match:", np.isclose(hand, thr_s[doy366(d0)-1,i,j]))

# also hand-check climatology for the same doy
vals_c = []
for off in range(-15, 16):
    dd = d0 + dt.timedelta(days=off)
    d = doy366(dd)
    def raw_mean(ddd):
        dd2 = doy366(ddd)
        pool = []
        for m, ed in enumerate(ext_days):
            if 1992 <= ed.year <= 2002 and doy366(ed) == dd2:
                pool.append(base_data[m-5:m+6, i, j])
        pool = np.concatenate(pool).astype(np.float64)
        return np.nanmean(pool)
    if d == 60:
        v = 0.5*(raw_mean(dd-dt.timedelta(days=1)) + raw_mean(dd+dt.timedelta(days=1)))
    else:
        v = raw_mean(dd)
    vals_c.append(v)
hand_c = float(np.mean(vals_c))
print("hand smoothed clim:", hand_c, "| vectorized:", clm_s[doy366(d0)-1,i,j], "| match:", np.isclose(hand_c, clm_s[doy366(d0)-1,i,j]))

# verify hot runs per cell: longest consecutive hot run anywhere
hot = tgt_data >= thr_s[np.array([doy366(dt.date(2004,6,1)+dt.timedelta(days=k)) for k in range(92)])-1]
sea = np.isfinite(tgt_data).all(axis=0)
hot[:, ~sea] = False
best = 0
for i in range(60):
    for j in range(60):
        if not sea[i,j]: continue
        run = 0
        for k in range(92):
            run = run+1 if hot[k,i,j] else 0
            best = max(best, run)
print("longest consecutive hot run in any cell:", best)
