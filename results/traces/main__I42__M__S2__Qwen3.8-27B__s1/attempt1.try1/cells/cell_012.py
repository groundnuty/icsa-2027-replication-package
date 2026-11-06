import numpy as np, pickle
from collections import defaultdict

time_all = np.load('/tmp/time_all.npy')
base_dates = time_all[3647:7675]

LEAP_CUM = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
def doy366(dates):
    dates = np.asarray(dates).astype('datetime64[D]')
    m = (dates.astype('datetime64[M]') - dates.astype('datetime64[Y]')).astype(int) + 1
    d = (dates - dates.astype('datetime64[M]')).astype(int) + 1
    return LEAP_CUM[m - 1] + d

bmin = np.datetime64('1992-01-01'); bmax = np.datetime64('2002-12-31')
pools = defaultdict(list)
for k in range(-5, 6):
    b = base_dates + np.timedelta64(k, 'D')
    msk = (b >= bmin) & (b <= bmax)
    idx = np.where(msk)[0]
    dval = doy366(b[msk])
    for i, dd in zip(idx.tolist(), dval.tolist()):
        pools[dd].append(i)

bad = {d: len(v) for d, v in pools.items() if len(v) != 121}
print("bad:", bad)
# examine one: count how many baseline dates have that doy
for d in bad:
    bsel = base_dates[(base_dates >= bmin) & (base_dates <= bmax)]
    cnt = np.sum(doy366(bsel) == d)
    print("doy", d, "has", cnt, "baseline dates")
