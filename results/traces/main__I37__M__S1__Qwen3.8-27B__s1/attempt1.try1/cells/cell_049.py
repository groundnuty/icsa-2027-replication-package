import datetime as dt, random
import numpy as np

ext = np.load('/work/chk/ext.npy').astype(np.float64)
sea = np.load('/work/chk/sea.npy')
thr = np.load('/work/chk/thr.npy')
tgt = np.load('/work/chk/tgt.npy').astype(np.float64)

def daterange(a, b):
    d, out = a, []
    while d <= b:
        out.append(d); d += dt.timedelta(days=1)
    return out
ext_dates = daterange(dt.date(1991,12,27), dt.date(2003,1,5))
doy_ext = np.array([dt.date(2000, d.month, d.day).timetuple().tm_yday for d in ext_dates])
doy_b = doy_ext[5:5+4018]

# 1) construction property: fraction of pool values >= hazen q90 of the pool
random.seed(0)
samples = random.sample(range(366), 25)
fracs = []
for d0 in samples:
    d = d0 + 1
    if d == 60:
        continue
    js = np.where(doy_b == d)[0]
    rows = (5 + js[:, None] + np.arange(-5, 6)[None, :]).ravel()
    for _ in range(3):
        i, j = random.randrange(60), random.randrange(60)
        if not sea[i, j]:
            continue
        pool = ext[rows, i, j]
        pv = pool[np.isfinite(pool)]
        if pv.size < 20:
            continue
        q = np.quantile(pv, 0.9, method='hazen')
        fracs.append((pv >= q).mean())
print("pool exceedance fraction: mean %.4f min %.4f max %.4f (n=%d)" %
      (np.mean(fracs), np.min(fracs), np.max(fracs), len(fracs)))

# 2) independent 2012 MHW pipeline (different style: scalar loops, different run logic)
tgt_dates = daterange(dt.date(2012,6,1), dt.date(2012,8,31))
doy_tgt = np.array([dt.date(2000, d.month, d.day).timetuple().tm_yday for d in tgt_dates])

def mhw_for_cell(hot):  # hot: list of bool, length 92
    n = len(hot)
    # find maximal hot runs
    runs = []
    t = 0
    while t < n:
        if hot[t]:
            s = t
            while t < n and hot[t]:
                t += 1
            runs.append([s, t - 1])
        else:
            t += 1
    seeds = [r for r in runs if r[1] - r[0] + 1 >= 5]
    merged = []
    for r in seeds:
        if merged and r[0] - merged[-1][1] - 1 <= 2:
            merged[-1][1] = max(merged[-1][1], r[1])
        else:
            merged.append([r[0], r[1]])
    return merged

n_hot_cells = 0
mhw_events_cells = []
hot_days_total = 0
for idx in np.argwhere(sea).tolist():
    i, j = idx
    hot = [bool(tgt[t, i, j] >= thr[int(doy_tgt[t]) - 1, i, j]) for t in range(92)]
    hot_days_total += sum(hot)
    ms = mhw_for_cell(hot)
    if ms:
        mhw_events_cells.append((i, j, ms))
print("independent: hot cell-days =", hot_days_total, " cells with MHWs:", len(mhw_events_cells))
for e in mhw_events_cells[:10]:
    print("   ", e)

# active days from independent per-cell masks
act = [False]*92
for (i, j, ms) in mhw_events_cells:
    for s, e in ms:
        for t in range(s, e + 1):
            act[t] = True
print("independent active days:", sum(act), [ (tgt_dates[t].isoformat()) for t in range(92) if act[t] ])
