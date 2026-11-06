import numpy as np, datetime, json
z = np.load('/work/region.npz'); s = np.load('/work/doy_stats.npz'); m = np.load('/work/mhw.npz')
tgt3 = z['tgt_sst'].reshape(92, 3600)
st2 = s['sm_thresh'].reshape(366, 3600)
raw_t = s['raw_thresh'].reshape(366, 3600)
tgt_doy = s['target_doy']
sea = m['sea']; mhw = m['mhw']
dates = [datetime.date.fromisoformat(x) for x in z['tgt_dates']]

# --- independent slow implementation: recompute pools from scratch in plain loops ---
base_dates = [datetime.date.fromisoformat(x) for x in z['base_dates']]
base_sst = z['base_sst']
CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
md = lambda d: CUM[d.month-1] + d.day
base_md = [md(d) for d in base_dates]

def pool_indices_slow(d):
    # d in 1..366, d != 60 : indices of dates within +/-5 days of any baseline anchor with month-day d
    out = set()
    for i, b in enumerate(base_dates):
        if datetime.date(1992,1,1) <= b <= datetime.date(2002,12,31) and base_md[i] == d:
            for k in range(-5, 6):
                j = i + k
                if 0 <= j < len(base_dates):
                    out.add(j)
    return sorted(out)

def hazen_slow(p, vals):
    x = sorted(v for v in vals if v == v)  # ignore NaN
    n = len(x)
    h = n*p + 0.5
    k = int(h // 1); g = h - k
    if k <= 0:
        return x[0] if g == 0 else x[0] + (x[1]-x[0])*g
    if k >= n:
        return x[-1]
    return x[k-1] + (x[k]-x[k-1])*g

# pick 40 random sea cells
rng = np.random.default_rng(42)
sea_cols = np.where(sea)[0]
sample = rng.choice(sea_cols, 40, replace=False)

# check smoothed threshold for the needed doys (153..244) matches slow recomputation
doys_needed = np.unique(tgt_doy)
maxdiff_t = 0.0
for col in sample:
    r, c = divmod(col, 60)
    for d in doys_needed:
        idx = pool_indices_slow(int(d))
        assert len(idx) == 121, (d, len(idx))
        vals = [float(base_sst[i, r, c]) for i in idx]
        thr = hazen_slow(0.90, vals)
        # slow 31-day wrap smoothing of raw thresholds: need raw thresholds of d-15..d+15
        def raw_thr(dd):
            idx2 = pool_indices_slow(dd) if dd != 60 else None
            if dd == 60:
                t59 = hazen_slow(0.90, [float(base_sst[i,r,c]) for i in pool_indices_slow(59)])
                t61 = hazen_slow(0.90, [float(base_sst[i,r,c]) for i in pool_indices_slow(61)])
                return 0.5*(t59+t61)
            return hazen_slow(0.90, [float(base_sst[i,r,c]) for i in idx2])
        win = [raw_thr(((int(d)-16+i) % 366) + 1) for i in range(31)]
        sm = sum(win)/31.0
        maxdiff_t = max(maxdiff_t, abs(sm - st2[int(d)-1, col]))
print("max |slow-smoothed-thr - stored-smoothed-thr| over 40 cells x 92 doys:", maxdiff_t)
print("PASS" if maxdiff_t < 1e-8 else "FAIL")
