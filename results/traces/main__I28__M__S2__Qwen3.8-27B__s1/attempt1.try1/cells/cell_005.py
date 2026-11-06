import numpy as np
import pandas as pd
import pickle
from datetime import date, timedelta

with open("/tmp/sst_data.pkl", "rb") as f:
    D = pickle.load(f)
sst_pool = D["sst_pool"]; sst_target = D["sst_target"]; sea = D["sea"]
time_pool = D["time_pool"]  # list of datetime, 4028 entries

# day-of-year per spec: month/day mapping, Feb29=60, Mar1=61...
CUM = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
def doy_spec(m, d):  # returns day-of-year per spec (1..366)
    return CUM[m-1] + d

# sanity checks
assert doy_spec(1,1)==1 and doy_spec(2,28)==59 and doy_spec(2,29)==60 and doy_spec(3,1)==61 and doy_spec(12,31)==366
assert doy_spec(6,1)==153 and doy_spec(8,31)==244

pool_start = date(1991,12,27)
N = len(time_pool)
assert N == 4028
pool_day0 = np.array([(d - pool_start).days for d in
                      [date(d.year,d.month,d.day) for d in time_pool]], dtype=np.int64)
# verify contiguity
assert (np.diff(pool_day0)==1).all() and pool_day0[0]==0

# Build membership matrix M[d, t]: pool date t within +-5 days of a baseline date (1992-2002) with doy_spec == d
M = np.zeros((366, N), dtype=bool)
for y in range(1992, 2003):
    leap = (y%4==0 and (y%100!=0 or y%400==0))
    for d in range(1, 367):
        if d == 60:
            continue
        if d > 60 and not leap:
            pos = d - 1   # actual day index within year
        elif d == 60:
            pos = 60
        else:
            pos = d
        b = date(y,1,1) + timedelta(days=pos-1)
        idx = (b - pool_start).days
        lo = max(0, idx-5); hi = min(N, idx+6)
        M[d, lo:hi] = True

# quick checks
# d=1: windows around Jan 1 of 1992..2002 -> first window starts 1991-12-27 (idx 0), last ends 2003-01-06? 2002-01-01+5 = 2002-01-06, ok inside
print("M[1] count:", M[1].sum(), "expected 11*11=121")
print("M[59] count:", M[59].sum(), "(Feb28 windows; leap yrs include Feb29 -> 11*11=121)")
print("M[61] count:", M[61].sum())
# check that Feb 29 1992 is in M[59] and M[61]
idx_19920229 = (date(1992,2,29)-pool_start).days
print("Feb29 1992 in pools d=59,61:", M[59, idx_19920229], M[61, idx_19920229], " d=60:", M[60, idx_19920229])
# and in d=54? (Feb23 window: Feb23+5=Feb28 in leap? no Feb23+5=Feb28, so Feb29 not included)
idx_19920223 = (date(1992,2,23)-pool_start).days
print("Feb29 1992 in pool d=58 (Feb27+2):", M[58, idx_19920229])
print("Feb29 1992 in pool d=65 (Mar5-4):", M[65, idx_19920229])
print("Feb29 1992 in pool d=54 (Feb23+5=Feb28):", M[54, idx_19920229])
# day 60 has no pool
assert not M[60].any()

# Check pool size for a normal d, e.g. d=153 (Jun 1): 11 windows x 11 days = 121
print("M[153] count:", M[153].sum())
np.save("/tmp/M.npy", M)
