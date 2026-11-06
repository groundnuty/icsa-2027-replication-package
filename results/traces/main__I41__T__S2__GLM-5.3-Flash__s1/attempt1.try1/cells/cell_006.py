import datetime as dt
import numpy as np

def doy_of(d: dt.date) -> int:
    n = (d - dt.date(d.year, 1, 1)).days + 1
    if (d.month >= 3) and not (d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0)):
        n += 1
    return n

tests = {(1992,1,1):1, (1992,2,28):59, (1992,2,29):60, (1992,3,1):61, (1992,12,31):366,
         (1993,2,28):59, (1993,3,1):61, (1993,12,31):366, (2000,2,29):60, (2000,3,1):61,
         (2001,3,1):61, (2001,12,31):366, (1996,3,1):61, (2021,6,1):153, (2021,8,31):244}
allok = True
for (y,m,dd), exp in tests.items():
    got = doy_of(dt.date(y,m,dd))
    if got != exp:
        allok = False
        print("MISMATCH", (y,m,dd), got, exp)
print("doy function:", "ALL OK" if allok else "ERRORS")

# vectorised via pandas: map each date to the special doy
# approach: for a date d, doy_special = (d - Jan1(d.year)).days + 1 + (1 if (not leap(year) and (d >= Mar1)) else 0)
def leap(y): return y%4==0 and (y%100!=0 or y%400==0)

# Pool construction plan (small test with fake data):
# baseline 1992-2002; for each doy d != 60: pool = SST on baseline dates whose date is within +-5 calendar days of any baseline date with doy == d.
# Equivalent per baseline date b with doy(b)=d: contributes its SST to pools of doys d-5..d+5 (each mapped specially, then excluding 60).
# Verify with small enumeration for doy 61 (Mar 1): baseline dates with doy 61 are Mar 1 of each baseline year (1992 leap: Mar1 -> doy 61; 1993: Mar 1 -> 61 etc.)
# Window: dates within +-5 days of those dates.
# e.g. 1993-03-01 +-5 => 1993-02-24..1993-03-06. doys of those dates: Feb24=55..Mar6=66. So pools 55..66 receive 1993-03-01's value.
# Let me verify by brute-force construction:
baseline = [dt.date(1992,1,1)+dt.timedelta(days=i) for i in range((dt.date(2002,12,31)-dt.date(1992,1,1)).days+1)]
doy_map = {b: doy_of(b) for b in baseline}
# brute force pools for doy 1, 59, 61, 366
def brute_pool_dates(d):
    # all baseline dates b such that doy(b)==d, then all dates within +-5 calendar days of b
    centers = [b for b in baseline if doy_map[b]==d]
    dates = []
    for c in centers:
        for k in range(-5,6):
            q = c + dt.timedelta(days=k)
            dates.append(q)
    return sorted(set(dates))
for d in [1, 59, 61, 60, 366]:
    ds_ = brute_pool_dates(d)
    if ds_:
        yrs = sorted(set(x.year for x in ds_))
        print("doy", d, ": n dates", len(ds_), "range", ds_[0], ds_[-1], "years", yrs[:3], "...", yrs[-3:])
    else:
        print("doy", d, ": empty (no pool of its own)")
