import numpy as np, datetime as dt, json

Z = np.load("/tmp/mhw/loaded.npz")
Vb, Vt = Z["Vb"], Z["Vt"]
BASE_START = dt.date(1991,12,27); BASE_END = dt.date(2003,1,5)
BL_START, BL_END = dt.date(1992,1,1), dt.date(2002,12,31)
TG_START, TG_END = dt.date(2012,6,1), dt.date(2012,8,31)

# day-of-year, leap calendar, by month/day (Jan 1=1 ... Feb 29=60 ... Dec 31=366)
leap_month = [31,29,31,30,31,30,31,31,30,31,30,31]
doy_of = {}
for m in range(1,13):
    start = 1
    for mm in range(1,m): start += leap_month[mm-1]
    for day in range(1, leap_month[m-1]+1):
        doy_of[(m,day)] = start + day - 1
assert doy_of[(1,1)]==1 and doy_of[(2,28)]==59 and doy_of[(2,29)]==60 and doy_of[(3,1)]==61 and doy_of[(12,31)]==366

def o2p(dd):  # ordinal -> Vb index
    return (dd - BASE_START).days

# baseline dates
bl_dates = [BL_START + dt.timedelta(days=i) for i in range((BL_END-BL_START).days+1)]
bl_ord = np.array([(dd.toordinal()-BASE_START.toordinal()) for dd in bl_dates])
bl_doy = np.array([doy_of[(dd.month,dd.day)] for dd in bl_dates])
print("baseline days:", len(bl_dates), "doy range:", bl_doy.min(), bl_doy.max(), "has 60:", (bl_doy==60).sum())

# W_d sets (Vb indices)
pools = {}
for d in range(1, 367):
    if d == 60: continue
    m = bl_doy == d
    offs = bl_ord[m][:,None] + np.arange(-5,6)[None,:]
    pools[d] = np.unique(offs)
sizes = {d: len(v) for d,v in pools.items()}
print("pool size min/max:", min(sizes.values()), max(sizes.values()))
print("day1 first/last idx:", pools[1].min(), pools[1].max(), "->", BASE_START+dt.timedelta(days=int(pools[1].min())), BASE_START+dt.timedelta(days=int(pools[1].max())))
print("day366 first/last:", BASE_START+dt.timedelta(days=int(pools[366].min())), BASE_START+dt.timedelta(days=int(pools[366].max())))
print("day59/61:", len(pools[59]), len(pools[61]))
# check overhang usage
print("W1 min date:", BASE_START+dt.timedelta(days=int(pools[1].min())), "W366 max date:", BASE_START+dt.timedelta(days=int(pools[366].max())))
print("any pool using 2003-01-05:", any(int(pools[d].max())==(dt.date(2003,1,5)-BASE_START).days for d in pools))
print("any pool using 1991-12-27:", any(int(pools[d].min())==0 for d in pools))
