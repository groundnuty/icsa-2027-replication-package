import numpy as np, json, datetime as dt, os, time

t0 = time.time()
data = np.load('/work/data.npy')  # (4120, 60, 60) float64
meta = json.load(open('/work/dates.json'))
bw = [dt.date.fromisoformat(s) for s in meta['baseline_window']]   # 1991-12-27..2003-01-05
tg = [dt.date.fromisoformat(s) for s in meta['target']]            # 2017-06-01..2017-08-31
n_bw = len(bw)
assert n_bw == 4028 and len(tg) == 92

# --- doy mapping (leap calendar by month/day): cum table
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def md_doy(d):
    return cum[d.month-1] + d.day
# sanity
assert md_doy(dt.date(1992,2,28)) == 59 and md_doy(dt.date(1992,2,29)) == 60
assert md_doy(dt.date(1993,3,1)) == 61 and md_doy(dt.date(1992,12,31)) == 366
assert md_doy(dt.date(2017,6,1)) == 153 and md_doy(dt.date(2017,8,31)) == 244

# --- date -> index in data
idx_of = {d:i for i,d in enumerate(bw)}

# --- pools: for doy d != 60, dates within +/-5 calendar days of each baseline (1992-2002) date with doy d
pools = {}
for d in range(1, 367):
    if d == 60:
        continue
    anchors = []
    # iterate baseline years 1992..2002, find dates with md_doy == d
    for y in range(1992, 2003):
        # find date in year y with month/day matching doy d
        # invert cum table
        m = 1
        while m < 12 and cum[m] < d:
            m += 1
        day = d - cum[m-1]
        try:
            ad = dt.date(y, m, day)
        except ValueError:
            continue  # e.g. Feb 29 in non-leap year
        if md_doy(ad) == d:
            anchors.append(ad)
    idxs = set()
    for a in anchors:
        for off in range(-5, 6):
            w = a + dt.timedelta(days=off)
            if w in idx_of:
                idxs.add(idx_of[w])
    pools[d] = np.array(sorted(idxs), dtype=np.int64)

sizes = np.array([len(pools[d]) for d in range(1,367) if d != 60])
print('pool size min/max:', sizes.min(), sizes.max())
print('pool[1] first/last date:', bw[pools[1][0]], bw[pools[1][-1]], 'n=', len(pools[1]))
print('pool[365] last date:', bw[pools[365][-1]], 'n=', len(pools[365]))
print('pool[366] dates n=', len(pools[366]), bw[pools[366][0]], bw[pools[366][-1]])
print('pool[59] includes leap Feb29?', any((bw[i].month,bw[i].day)==(2,29) for i in pools[59]))
print('pool[61] includes leap Feb29?', any((bw[i].month,bw[i].day)==(2,29) for i in pools[61]))
print('pool setup time', round(time.time()-t0,1),'s')
np.save('/work/pool_sizes.npy', sizes)
import pickle
with open('/work/pools.pkl','wb') as f: pickle.dump(pools, f)
