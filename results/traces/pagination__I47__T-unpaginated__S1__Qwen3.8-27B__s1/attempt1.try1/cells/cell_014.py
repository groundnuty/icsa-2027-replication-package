
import numpy as np
from datetime import date

# 1) Verify numpy hazen = HF type 5: h = n*p + 0.5 (1-based), linear interp
x = np.arange(1.0, 11.0)
q = np.quantile(x, 0.9, method='hazen')
n = len(x)
h = n*0.9 + 0.5  # = 9.5
print("hazen q(0.9) of 1..10:", q, " expected:", 0.5*(x[8]+x[9]))
q50 = np.quantile(x, 0.5, method='hazen')
print("hazen q(0.5):", q50, " expected:", 5.5)

# 2) nanquantile with per-row differing NaN counts
a = np.array([[1,2,3,4,5,np.nan],[1,2,3,4,np.nan,np.nan]])
r = np.nanquantile(a, 0.9, method='hazen', axis=1)
# row0: n=5 h=5.0 -> 5 ; row1: n=4 h=4.1 -> clamp to 4
print("nanquantile:", r, " expected: [5 4]")
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("error")
    try:
        np.nanquantile(np.array([np.nan, np.nan]), 0.9, method='hazen', axis=0)
    except Exception as e:
        print("all-NaN raises:", type(e).__name__)
print("nanmean all-NaN warns:", end=" ")
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    v = np.nanmean(np.array([np.nan, np.nan]))
    print("n warnings:", len(w), "value:", v)

# 3) doy mapping by month/day (leap-year table)
cuml = [31,31+29,31+29+31,31+29+31+30,31+29+31+30+31,31+29+31+30+31+30,
        31+29+31+30+31+30+31,31+29+31+30+31+30+31+31,31+29+31+30+31+30+31+31+30,
        31+29+31+30+31+30+31+31+30+31,31+29+31+30+31+30+31+31+30+31+30]
def doy(d):
    return (cuml[d.month-1] if d.month > 1 else 0) + d.day
assert doy(date(2000,2,28)) == 59 and doy(date(2000,2,29)) == 60 and doy(date(2000,3,1)) == 61
assert doy(date(1995,12,31)) == 365 and doy(date(2000,12,31)) == 366
assert doy(date(2019,6,1)) == 152 and doy(date(2019,8,31)) == 243
print("doy checks OK")

# 4) sanity: count of days in each range
from datetime import timedelta
def cnt(d0, d1):
    return (d1 - d0).days + 1
print("buffer:", cnt(date(1991,12,27), date(2003,1,5)), "baseline:", cnt(date(1992,1,1), date(2002,12,31)), "target:", cnt(date(2019,6,1), date(2019,8,31)))
