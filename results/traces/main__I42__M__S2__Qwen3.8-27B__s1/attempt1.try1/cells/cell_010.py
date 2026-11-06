import numpy as np
from collections import defaultdict

base = np.load('/tmp/base.npy')
target = np.load('/tmp/target.npy')
time_all = np.load('/tmp/time_all.npy')
base_dates = time_all[3647:7675]
target_dates = time_all[11109:11201]

LEAP_CUM = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
def doy366(dates):
    dates = np.asarray(dates)
    m = (dates.astype('datetime64[M]') - dates.astype('datetime64[Y]')).astype(int) + 1
    d = (dates - dates.astype('datetime64[M]')).astype(int) + 1
    return LEAP_CUM[m - 1] + d

checks = [('1993-03-01', 61), ('2012-06-01', 153), ('2012-08-31', 244),
          ('1992-02-29', 60), ('2002-12-31', 366), ('1991-12-27', 362), ('2012-02-28', 59)]
for s, exp in checks:
    got = int(doy366(np.array(s, dtype='datetime64[D]')))
    assert got == exp, (s, got, exp)
print("doy mapping OK")

doy_base = doy366(base_dates)
doy_target = doy366(target_dates)
print("target doy range:", doy_target.min(), doy_target.max(), "unique count:", len(set(doy_target.tolist())))

bmin = np.datetime64('1992-01-01'); bmax = np.datetime64('2002-12-31')
pools = defaultdict(list)
for k in range(-5, 6):
    b = base_dates + np.timedelta64(k, 'D')
    msk = (b >= bmin) & (b <= bmax)
    idx = np.where(msk)[0]
    dval = doy366(b[msk])
    for i, dd in zip(idx.tolist(), dval.tolist()):
        pools[dd].append(i)

missing = [d for d in range(1, 367) if d != 60 and d not in pools]
assert not missing, missing
assert all(len(pools[d]) == 121 for d in pools), sorted({len(v) for v in pools.values()})
print("pools:", len(pools), "all size 121; day 60 absent:", 60 not in pools)

# spot check: pool for day 1 (Jan 1) should be dates within 5d of each Jan 1 in 1992..2002
p1 = sorted(pools[1])
print("pool d=1 first/last base dates:", base_dates[p1[0]], base_dates[p1[-1]])
print("count:", len(p1))
import pickle
with open('/tmp/pools.pkl', 'wb') as f:
    pickle.dump({d: np.array(v) for d, v in pools.items()}, f)
