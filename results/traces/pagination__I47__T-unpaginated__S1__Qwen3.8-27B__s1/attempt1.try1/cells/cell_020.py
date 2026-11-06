
import numpy as np, time, json
from datetime import date, timedelta

t0 = time.time()
buf = np.load('/work/bs.npy')
tgt = np.load('/work/tg.npy')
sea = np.load('/work/sea.npy')

def get_dates(d0, d1):
    out, cur = [], d0
    while cur <= d1:
        out.append(cur); cur += timedelta(days=1)
    return out
buf_dates = get_dates(date(1991,12,27), date(2003,1,5))
tgt_dates = get_dates(date(2019,6,1), date(2019,8,31))

cuml = np.cumsum([0,31,29,31,30,31,30,31,31,30,31,30,31])
def doy(d):
    return int(cuml[d.month-1] + d.day)

bs0, bs1 = date(1992,1,1), date(2002,12,31)
pools = {d: [] for d in range(1, 367)}
for i, t in enumerate(buf_dates):
    for o in range(-5, 6):
        b = t + timedelta(days=o)
        if bs0 <= b <= bs1:
            pools[doy(b)].append(i)
print("pool sizes ok:", all(len(pools[d]) == 121 for d in range(1,367) if d != 60), "d60:", len(pools[60]))

thr = np.empty((366, 3311))
clim = np.empty((366, 3311))
for d in range(1, 367):
    if d == 60:
        continue
    X = buf[pools[d]]
    clim[d-1] = X.mean(axis=0)
    thr[d-1] = np.quantile(X, 0.9, axis=0, method='hazen')
thr[59] = 0.5 * (thr[58] + thr[60])
clim[59] = 0.5 * (clim[58] + clim[60])
assert np.isfinite(thr).all() and np.isfinite(clim).all(), "non-finite thr/clim"

idx = (np.arange(366)[:, None] - 15 + np.arange(31)[None, :]) % 366   # (366,31)
thr_s = thr[idx].mean(axis=1)   # (366, 3311)
clim_s = clim[idx].mean(axis=1)
assert thr_s.shape == (366, 3311) and clim_s.shape == (366, 3311)
print("thr_s shape ok")
np.save('/work/thr_s.npy', thr_s)
np.save('/work/clim_s.npy', clim_s)

tdoy = np.array([doy(d) for d in tgt_dates])
assert tdoy[0] == 153 and tdoy[-1] == 244 and len(np.unique(tdoy)) == 92
hot = tgt[:, sea] >= thr_s[tdoy - 1]
print("hot fraction: %.5f" % hot.mean(), "max thr:", float(thr_s.max()), "min thr:", float(thr_s.min()))

N = 92
mhw_cell = np.zeros((N, 3311), dtype=bool)
for c in range(3311):
    h = hot[:, c]
    if not h.any():
        continue
    d = np.diff(np.concatenate(([0], h.view(np.int8), [0])))
    starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1
    merged = []
    for s, e in zip(starts, ends):
        if e - s + 1 >= 5:
            if merged and s - merged[-1][1] - 1 <= 2:
                merged[-1][1] = e
            else:
                merged.append([s, e])
    for s, e in merged:
        mhw_cell[s:e+1, c] = True
print("cell-MHW days:", int(mhw_cell.sum()))

active = mhw_cell.any(axis=1)
d = np.diff(np.concatenate(([0], active.view(np.int8), [0])))
es, ee = np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1
events = [(tgt_dates[s].isoformat(), tgt_dates[e].isoformat(), int(e-s+1)) for s, e in zip(es, ee)]
for ev in events:
    print("event:", ev[0], "->", ev[1], "len", ev[2])

np.save('/work/mhw_cell.npy', mhw_cell)
json.dump({"events": [{"onset": a, "end": b, "len": L} for a, b, L in events],
           "active_days": int(active.sum()), "hot_days": int(hot.sum())},
          open('/work/intermediate.json', 'w'))
print("time %.1f s" % (time.time()-t0))
