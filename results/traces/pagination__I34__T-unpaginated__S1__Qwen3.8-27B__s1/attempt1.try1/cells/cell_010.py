
import numpy as np, datetime

# sanity check numpy hazen = Hyndman-Fan type 5
x = np.arange(1, 11, dtype=float)
print("hazen p=0.9 n=10:", np.quantile(x, 0.9, method="hazen"), "expect 9.5 (HF type5: (n-0.5)*p 1-based)")

ord2date = {o: datetime.date.fromordinal(o) for o in range(19910, 20040)}  # plenty

# DOY mapping by (month, day)
cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366]
def doy_of(d):
    return cum[d.month - 1] + d.day  # Jan1=1, Feb28=59, Feb29=60, Mar1=61, Dec31=366
assert doy_of(datetime.date(2004, 2, 29)) == 60
assert doy_of(datetime.date(2004, 3, 1)) == 61
assert doy_of(datetime.date(2007, 12, 31)) == 366
assert doy_of(datetime.date(2007, 1, 1)) == 1
assert doy_of(datetime.date(2007, 2, 28)) == 59

b_dates = np.load("/tmp/mhw/baseline_dates.npy")
d0 = datetime.date.fromordinal(int(b_dates[0])); d1 = datetime.date.fromordinal(int(b_dates[-1]))
print("loaded range:", d0, d1, "n =", len(b_dates))
assert str(d0) == "1991-12-27" and str(d1) == "2003-01-05"

base_start = datetime.date(1992, 1, 1).toordinal()
base_end = datetime.date(2002, 12, 31).toordinal()

# For each ext date index i, set of doy values d such that ext date is within +-5 days of a baseline date with doy d.
S = []  # list of lists of doy
for o in b_dates:
    lo = max(int(o) - 5, base_start)
    hi = min(int(o) + 5, base_end)
    doys = set()
    for so in range(lo, hi + 1):
        doys.add(doy_of(datetime.date.fromordinal(so)))
    S.append(sorted(doys))

# index lists per doy
idx_by_doy = {d: [] for d in range(1, 367) if d != 60}
for i, s in enumerate(S):
    for d in s:
        idx_by_doy[d].append(i)
sizes = {d: len(v) for d, v in idx_by_doy.items()}
from collections import Counter
print("pool size distribution:", Counter(sizes.values()))
# check a few
print("doy 1:", sizes[1], "doy 61:", sizes[61], "doy 366:", sizes[366], "doy 153 (Jun1):", sizes[153], "doy 244 (Aug31):", sizes[244])

# verify: doy 1 pool should be dates 1991-12-27..1992-01-05 (9 days from 1992-01-01 window) plus other years' Jan1 windows (41 each, 10 more years)
v = idx_by_doy[1]
print("doy1 first dates:", [str(datetime.date.fromordinal(int(b_dates[i]))) for i in v[:9]])
print("doy1 last dates:", [str(datetime.date.fromordinal(int(b_dates[i]))) for i in v[-5:]])
