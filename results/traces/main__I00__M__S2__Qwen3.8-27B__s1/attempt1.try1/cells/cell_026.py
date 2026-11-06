import numpy as np, datetime as dt, os
doy = np.load("/tmp/doy.npy")
base = dt.date(1991,12,27)
def doy_of(d):
    k = (d - base).days
    return int(doy[k]) if 0 <= k < len(doy) else None
month_days = np.cumsum([0,31,29,31,30,31,30,31,31,30,31,30,31])
ref = lambda d: month_days[d.month-1] + d.day
for d in [dt.date(2004,1,1), dt.date(2004,2,28), dt.date(2004,2,29), dt.date(2004,3,1),
          dt.date(2003,2,28), dt.date(2003,3,1), dt.date(1991,12,30), dt.date(1991,12,31),
          dt.date(2002,12,31), dt.date(2003,1,5), dt.date(2004,6,1), dt.date(2004,8,31)]:
    k = (d - base).days
    ok = (0 <= k < len(doy)) and int(doy[k]) == ref(d)
    print(d, "doy:", doy_of(d), "ref:", ref(d), "OK" if ok else "MISMATCH")

# pool membership spot check: 1992-02-29 (doy 60) must be in pools of doys of 2/24..3/5 centers
idx60 = (dt.date(1992,2,29) - base).days
pools = {d: [] for d in range(1,367)}
ord0 = (dt.date(1992,1,1) - base).days
ord1 = (dt.date(2002,12,31) - base).days
for k in range(ord0, ord1+1):
    d = int(doy[k])
    pools[d] += [k+off for off in range(-5,6)]
in_ = [d for d in range(1,367) if idx60 in set(pools[d])]
print("doy-60 date 1992-02-29 belongs to pools of doys:", in_)
# expect 55..59 and 61..65
print("expected:", list(range(55,60))+list(range(61,66)))
print("cwd:", os.getcwd())
print(os.listdir("."))
