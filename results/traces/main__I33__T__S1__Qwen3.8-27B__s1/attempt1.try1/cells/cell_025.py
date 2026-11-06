
import numpy as np, datetime, os, time
t0=time.time()
os.makedirs('/work/work', exist_ok=True)

# ---- load all days ----
def load_day(p): return np.fromfile(p, dtype=np.float64).reshape(60,60)

base_dates = []
d = datetime.date(1991,12,27)
while d <= datetime.date(2003,1,5):
    base_dates.append(d); d += datetime.timedelta(days=1)
target_dates = []
d = datetime.date(2014,6,1)
while d <= datetime.date(2014,8,31):
    target_dates.append(d); d += datetime.timedelta(days=1)
print("n base dates:", len(base_dates), "n target:", len(target_dates))

S_base = np.stack([load_day(f"/work/ext/e_{x.strftime('%Y%m%d')}.npy") for x in base_dates])  # (4028,60,60)
S_t    = np.stack([load_day(f"/work/ext/e_{x.strftime('%Y%m%d')}.npy") for x in target_dates])  # (92,60,60)
print("loaded", S_base.shape, S_t.shape, round(time.time()-t0,1), "s")

# ---- day-of-year mapping (leap-year layout) ----
leap_cum = np.zeros(13, int); ml = [31,29,31,30,31,30,31,31,30,31,30,31]
for m in range(1,13): leap_cum[m+1] = leap_cum[m] + ml[m-1]
def doy(dt): return int(leap_cum[dt.month] + dt.day)

# check anchors
for dt in [datetime.date(2000,1,1), datetime.date(2000,2,28), datetime.date(2000,2,29), datetime.date(2000,3,1), datetime.date(2000,12,31), datetime.date(2014,6,1)]:
    print(dt, doy(dt))

# ---- sea cells ----
finite_all = np.all(np.isfinite(S_t), axis=0)  # (60,60)
sea = np.argwhere(finite_all)
print("sea cells:", sea.shape[0], "of 3600")
print("land per day (target):", [int((~np.isfinite(S_t[k])).sum()) for k in [0,45,91]])

# ---- pool date indices per doy ----
date2idx = {dt: i for i, dt in enumerate(base_dates)}
baseline_dates = [datetime.date(1992,1,1) + datetime.timedelta(days=k) for k in range((datetime.date(2002,12,31)-datetime.date(1992,1,1)).days + 1)]
doy_of_base = {i: doy(dt) for i, dt in enumerate(base_dates) if datetime.date(1992,1,1) <= dt <= datetime.date(2002,12,31)}
print("n baseline dates:", len(doy_of_base))

pool_idx = {}
by_doy = {}
for i, dt in enumerate(base_dates):
    if datetime.date(1992,1,1) <= dt <= datetime.date(2002,12,31):
        by_doy.setdefault(doy(dt), []).append(i)
for d in range(1, 367):
    if d == 60: continue
    s = set()
    for bi in by_doy.get(d, []):
        for k in range(-5, 6):
            s.add(bi + k)
    pool_idx[d] = np.array(sorted(s), dtype=int)

# verify pool date ranges and sizes
print("pool sizes: d=1:", len(pool_idx[1]), "d=59:", len(pool_idx[59]), "d=61:", len(pool_idx[61]), "d=153:", len(pool_idx[153]), "d=366:", len(pool_idx[366]))
print("d=1 dates:", base_dates[pool_idx[1][0]], "...", base_dates[pool_idx[1][-1]])
print("d=366 dates:", base_dates[pool_idx[366][0]], "...", base_dates[pool_idx[366][-1]])
print("d=59 date range:", base_dates[pool_idx[59][0]], "...", base_dates[pool_idx[59][-1]])
# check d=59 pool includes leap Feb 29 values
feb29s = [i for i,dt in enumerate(base_dates) if dt.month==2 and dt.day==29]
print("leap Feb29 idxs in pool 59:", [i in set(pool_idx[59].tolist()) for i in feb29s])
print("leap Feb29 idxs in pool 61:", [i in set(pool_idx[61].tolist()) for i in feb29s])

np.save('/work/work/S_base.npy', S_base)
np.save('/work/work/S_t.npy', S_t)
np.save('/work/work/pool_idx.npy', np.array([pool_idx[d] for d in [0]+list(range(1,60))+list(range(61,367))], dtype=object), allow_pickle=True)
np.save('/work/work/sea.npy', sea)
print("saved; total time", round(time.time()-t0,1))
