import numpy as np, pickle, datetime as dt, collections

D = pickle.load(open("/tmp/mhw_data.pkl","rb"))
base_dates = D["base_dates"]
nb = len(base_dates)

mlen = [31,29,31,30,31,30,31,31,30,31,30,31]
month_start = [0]
for m in mlen: month_start.append(month_start[-1]+m)
assert month_start[-1] == 366
def doy(d):
    return month_start[d.month-1] + d.day
assert doy(dt.date(1992,2,28))==59 and doy(dt.date(1992,2,29))==60 and doy(dt.date(1992,3,1))==61
assert doy(dt.date(1993,3,1))==61
assert doy(dt.date(2012,12,31))==366 and doy(dt.date(2002,12,31))==366
assert doy(dt.date(2012,6,1))==153 and doy(dt.date(2012,8,31))==244
print("doy mapping OK (fixed calendar by month/day)")

date_to_i = {d:i for i,d in enumerate(base_dates)}
base_centers = [d for d in base_dates if dt.date(1992,1,1) <= d <= dt.date(2002,12,31)]
print("n baseline centers:", len(base_centers))

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
cnt = collections.Counter(sizes.values())
print("pool sizes distribution:", cnt)
i29 = date_to_i[dt.date(1992,2,29)]
print("1992-02-29 pool membership:", {d: bool(masks[d][i29]) for d in (54,55,56,59,61,64,65,66)})
pickle.dump({"masks":masks}, open("/tmp/mhw_masks.pkl","wb"))
print("masks saved")