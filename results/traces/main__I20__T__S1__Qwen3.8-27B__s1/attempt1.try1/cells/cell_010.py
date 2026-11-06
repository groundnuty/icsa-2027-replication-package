import numpy as np, pickle, datetime as dt

D = pickle.load(open("/tmp/mhw_data.pkl","rb"))
base_dates = D["base_dates"]  # 1991-12-27..2003-01-05 contiguous
nb = len(base_dates); nlat, nlon = D["T"].shape[1:]

# --- 366-day calendar day-of-year mapping ---
mlen = [31,29,31,30,31,30,31,31,30,31,30,31]
month_start = [0]
for m in mlen: month_start.append(month_start[-1]+m)
assert month_start[-1] == 366
def doy(d):
    return month_start[d.month-1] + d.day  # 1..366, Feb29=60, non-leap has no 60
# checks
assert doy(dt.date(1992,2,28))==59 and doy(dt.date(1992,2,29))==60 and doy(dt.date(1992,3,1))==61
assert doy(dt.date(1993,3,1))==61 and doy(dt.date(2012,12,31))==366 and doy(dt.date(2002,12,31))==365
assert doy(dt.date(2012,6,1))==153 and doy(dt.date(2012,8,31))==244
print("doy mapping OK")

date_to_i = {d:i for i,d in enumerate(base_dates)}
# baseline dates (centers of windows)
base_centers = [d for d in base_dates if dt.date(1992,1,1) <= d <= dt.date(2002,12,31)]
print("n baseline centers:", len(base_centers))

# pool masks: for d in 1..366 (skip 60): union of [t-5, t+5] over centers with doy d
masks = {}
for d in range(1,367):
    if d == 60: continue
    m = np.zeros(nb, dtype=bool)
    for t in base_centers:
        if doy(t) == d:
            lo = date_to_i[t - dt.timedelta(days=5)]
            hi = date_to_i[t + dt.timedelta(days=5)]
            m[lo:hi+1] = True
    masks[d] = m
sizes = {d:int(m.sum()) for d,m in masks.items()}
import collections
cnt = collections.Counter(sizes.values())
print("pool sizes distribution:", cnt)
# day 366 should be 3*11=33; day 61 window includes Feb29? check 1992-02-29 in mask 59 and 61 and 55? 
i29 = date_to_i[dt.date(1992,2,29)]
for d in (54,55,56,59,60,61,64,65,66):
    if d in masks: print("1992-02-29 in pool", d, ":", bool(masks[d][i29]))
pickle.dump({"masks":masks}, open("/tmp/mhw_masks.pkl","wb"))
print("masks saved")