import numpy as np
from collections import defaultdict

base = np.load('/tmp/base.npy')      # (4028, 60, 60) float64, 1991-12-27..2003-01-05
target = np.load('/tmp/target.npy')  # (92, 60, 60) float64, 2012-06-01..2012-08-31
time_all = np.load('/tmp/time_all.npy')
base_dates = time_all[3647:7675]
target_dates = time_all[11109:11201]
print("base dates:", base_dates[0], base_dates[-1], len(base_dates))
print("target dates:", target_dates[0], target_dates[-1], len(target_dates))

LEAP_CUM = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
def doy366(dates):
    dates = np.asarray(dates)
    m = (dates.astype('datetime64[M]') - dates.astype('datetime64[Y]')).astype(int) + 1
    d = (dates - dates.astype('datetime64[M]')).astype(int) + 1
    return LEAP_CUM[m - 1] + d

# sanity checks on doy mapping
checks = [('1993-03-01', 61), ('2012-06-01', 153), ('2012-08-31', 244),
          ('1992-02-29', 60), ('2002-12-31', 366), ('1991-12-27', 365)]
for s, exp in checks:
    got = int(doy366(np.array(s, dtype='datetime64[D]')))
    assert got == exp, (s, got, exp)
print("doy mapping OK")

doy_base = doy366(base_dates)
doy_target = doy366(target_dates)
print("target doy range:", doy_target.min(), doy_target.max())

# Build pools: for each baseline-window date c (index i), for k in -5..5,
# if b = c+k is a baseline date (1992-01-01..2002-12-31), then c joins pool doy366(b)
bmin = np.datetime64('1992-01-01'); bmax = np.datetime64('2002-12-31')
pools = defaultdict(list)
for k in range(-5, 6):
    b = base_dates + np.timedelta64(k, 'D')
    msk = (b >= bmin) & (b <= bmax)
    idx = np.where(msk)[0]
    dval = doy366(b[msk])
    for i, dd in zip(idx.tolist(), dval.tolist()):
        pools[dd].append(i)

sizes = sorted(len(pools[d]) for d in pools)
print("pools:", len(pools), "size min/max:", sizes[0], sizes[-1])
# every d except 60 should be present, size 121
missing = [d for d in range(1, 367) if d != 60 and d not in pools]
assert not missing, missing
assert all(len(pools[d]) == 121 for d in pools), "unexpected pool sizes"
print("pool sizes all 121; day 60 absent from pools:", 60 not in pools)
np.save('/tmp/pool_idx.npy', {str(d): np.array(v) for d, v in pools.items()}, allow_pickle=True)
