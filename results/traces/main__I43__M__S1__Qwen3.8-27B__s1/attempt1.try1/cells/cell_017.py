import pickle
from datetime import date, timedelta

# day-of-year by month/day, leap-year calendar (1 Jan=1 ... 31 Dec=366, 29 Feb=60)
leap_cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy(d):
    return leap_cum[d.month-1] + d.day
# sanity checks
assert doy(date(2017,1,1))==1
assert doy(date(2017,2,28))==59
assert doy(date(2000,2,29))==60
assert doy(date(2017,3,1))==61
assert doy(date(2017,12,30))==365
assert doy(date(2017,12,31))==366
assert doy(date(2016,12,31))==366  # non-leap Dec 31 still 366 by (month,day) mapping

d0 = date(1991,12,27); d1 = date(2003,1,5)
dates = []
cur = d0
while cur <= d1:
    dates.append(cur); cur += timedelta(days=1)
print("n dates:", len(dates))
dpos = {d:i for i,d in enumerate(dates)}

b0 = date(1992,1,1); b1 = date(2002,12,31)
pools = {}
cur = b0
while cur <= b1:
    dd = doy(cur)
    if dd != 60:
        idxs = pools.setdefault(dd, [])
        for k in range(-5,6):
            t = cur + timedelta(days=k)
            assert d0 <= t <= d1
            idxs.append(dpos[t])
    cur += timedelta(days=1)

print("n pool days:", len(pools))
bad = {d:len(v) for d,v in pools.items() if len(v)!=121 or len(set(v))!=121}
print("pools without exactly 121 distinct dates:", bad)
# examples
print("d=1 first/last:", dates[pools[1][0]], dates[pools[1][-1]])
print("d=366 first/last:", dates[pools[366][0]], dates[pools[366][-1]])
print("d=59 first/last:", dates[pools[59][0]], dates[pools[59][-1]])
print("d=61 first/last:", dates[pools[61][0]], dates[pools[61][-1]])
# check 29 Feb values appear in neighbour pools (d=59 and d=61 of leap years)
feb29 = date(1996,2,29)
for dd in (59,60,61):
    if dd in pools:
        print("feb29 1996 in pool d=%d:" % dd, dpos[feb29] in pools[dd])
pickle.dump({"dates":dates, "pools":pools}, open("/tmp/pools.pkl","wb"))
print("saved /tmp/pools.pkl")
