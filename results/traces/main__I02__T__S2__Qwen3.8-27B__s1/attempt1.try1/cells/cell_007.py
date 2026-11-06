import numpy as np, pickle
from datetime import date, timedelta
z = np.load('work/sst.npz')
tb = z['tb']
date_to_i = {date.fromisoformat(ts.astype('datetime64[D]').astype(str)): i for i, ts in enumerate(tb)}
doy_md = {}
d = date(2004, 1, 1)
for k in range(366):
    doy_md[k+1] = (d.month, d.day)
    d += timedelta(days=1)

pool_idx = {}
for dd in range(1, 367):
    if dd == 60: continue
    m, day = doy_md[dd]
    idxs, seen = [], set()
    for y in range(1992, 2003):
        b = date(y, m, day)
        for delta in range(-5, 6):
            dt = b + timedelta(days=delta)
            assert date(1991,12,27) <= dt <= date(2003,1,5), (dd, y, delta, dt)
            if dt not in seen:
                seen.add(dt)
                idxs.append(date_to_i[dt])
    pool_idx[dd] = np.asarray(idxs, dtype=np.int64)
print("pool sizes:", {len(v) for v in pool_idx.values()}, "| n d values:", len(pool_idx))
def s(i): return tb[i].astype(str)
print("d=1 first:", [s(i) for i in pool_idx[1][:6]], "last:", [s(i) for i in pool_idx[1][-6:]])
print("d=366 last:", [s(i) for i in pool_idx[366][-6:]])
print("d=59 has 1996-02-29:", s(date_to_i[date(1996,2,29)]) in {s(i) for i in pool_idx[59]})
with open('work/pool_idx.pkl','wb') as fh: pickle.dump(pool_idx, fh)
print("pools saved")
