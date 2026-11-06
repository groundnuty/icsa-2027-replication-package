
import numpy as np, datetime, os, time
t0=time.time()
os.makedirs('/work/work', exist_ok=True)

def load_day(p): return np.fromfile(p, dtype=np.float64).reshape(60,60)

base_dates = []
d = datetime.date(1991,12,27)
while d <= datetime.date(2003,1,5):
    base_dates.append(d); d += datetime.timedelta(days=1)
target_dates = []
d = datetime.date(2014,6,1)
while d <= datetime.date(2014,8,31):
    target_dates.append(d); d += datetime.timedelta(days=1)

S_base = np.stack([load_day(f"/work/ext/e_{x.strftime('%Y%m%d')}.npy") for x in base_dates])
S_t    = np.stack([load_day(f"/work/ext/e_{x.strftime('%Y%m%d')}.npy") for x in target_dates])
print("loaded", S_base.shape, S_t.shape, round(time.time()-t0,1), "s")

# ---- day-of-year mapping (leap-year layout) ----
ml = [31,29,31,30,31,30,31,31,30,31,30,31]
leap_cum = np.zeros(13, int)
for m in range(12): leap_cum[m+1] = leap_cum[m] + ml[m]
def doy(dt): return int(leap_cum[dt.month-1] + dt.day)

for dt in [datetime.date(2000,1,1), datetime.date(2000,2,28), datetime.date(2000,2,29), datetime.date(2000,3,1), datetime.date(2000,12,31), datetime.date(2014,6,1)]:
    print(dt, doy(dt))

# ---- sea cells ----
finite_all = np.all(np.isfinite(S_t), axis=0)
sea = np.argwhere(finite_all)
print("sea cells:", sea.shape[0], "of 3600")

# ---- pool date indices per doy ----
baseline_dates = [datetime.date(1992,1,1) + datetime.timedelta(days=k) for k in range((datetime.date(2002,12,31)-datetime.date(1992,1,1)).days + 1)]
by_doy = {}
date2idx = {dt: i for i, dt in enumerate(base_dates)}
for dt in baseline_dates:
    by_doy.setdefault(doy(dt), []).append(date2idx[dt])
print("n baseline dates:", sum(len(v) for v in by_doy.values()), "distinct doys in baseline:", len(by_doy), "max doy present:", max(by_doy))

pool_idx = {}
for d in range(1, 367):
    if d == 60: continue
    s = set()
    for bi in by_doy.get(d, []):
        for k in range(-5, 6):
            s.add(bi + k)
    pool_idx[d] = np.array(sorted(s), dtype=int)

print("pool sizes: d=1:", len(pool_idx[1]), "d=59:", len(pool_idx[59]), "d=61:", len(pool_idx[61]), "d=153:", len(pool_idx[153]), "d=366:", len(pool_idx[366]))
print("d=1 dates:", base_dates[pool_idx[1][0]], "...", base_dates[pool_idx[1][-1]])
print("d=366 dates:", base_dates[pool_idx[366][0]], "...", base_dates[pool_idx[366][-1]])
print("d=59 range:", base_dates[pool_idx[59][0]], "...", base_dates[pool_idx[59][-1]])
feb29s = [i for i,dt in enumerate(base_dates) if dt.month==2 and dt.day==29]
print("leap Feb29 in pool 59:", [i in set(pool_idx[59].tolist()) for i in feb29s])
print("leap Feb29 in pool 61:", [i in set(pool_idx[61].tolist()) for i in feb29s])

# verify boundary: pool(1) should include 1991-12-27..1992-01-06 from B=1992-01-01
print("pool1 first 8 dates:", [base_dates[i] for i in pool_idx[1][:8]])
print("pool366 last 8 dates:", [base_dates[i] for i in pool_idx[366][-8:]])

np.save('/work/work/S_base.npy', S_base)
np.save('/work/work/S_t.npy', S_t)
import pickle
with open('/work/work/pool_idx.pkl','wb') as f:
    pickle.dump(pool_idx, f)
with open('/work/work/dates.pkl','wb') as f:
    pickle.dump({'base': base_dates, 'target': target_dates, 'sea': sea}, f)
print("saved; total time", round(time.time()-t0,1))
