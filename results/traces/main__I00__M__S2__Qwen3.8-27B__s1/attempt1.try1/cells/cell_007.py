import numpy as np, datetime as dt

# sanity: hazen quantile
a = np.array([1.,2,3,4,5])
print("hazen q90 of 1..5:", np.quantile(a, 0.9, method='hazen'))  # expect 4.0 (h=5*0.9=4.5? check)
print("linear q90 of 1..5:", np.quantile(a, 0.9, method='linear'))

S = np.load("/tmp/S.npy")  # (3600 cells, 4632 days) days: 1991-12-27 .. 2004-08-31
ncells, ndays = S.shape
print("S:", S.shape)

# --- dates and day-of-year (leap-year mapping 1..366) ---
base = dt.date(1991,12,27)
dates = [base + dt.timedelta(days=k) for k in range(ndays)]
month_days = np.cumsum([0,31,29,31,30,31,30,31,31,30,31,30,31])
doy = np.array([month_days[d.month-1] + d.day for d in dates])
print("doy range:", doy.min(), doy.max())
d60 = np.where(doy == 60)[0]
print("day-60 dates:", [str(dates[i]) for i in d60])

# global index of a date
def gidx(d):  # date -> index
    k = (d - base).days
    return k
ord0 = gidx(dt.date(1992,1,1)); ord1 = gidx(dt.date(2002,12,31))
print("baseline ordinal span (global idx):", ord0, ord1)

# --- build pools: for each baseline date b (1992-01-01..2002-12-31) with doy d, add window b-5..b+5 to pool[d] ---
pools = {d: [] for d in range(1,367)}
for k in range(ord0, ord1+1):
    d = int(doy[k])
    for off in range(-5,6):
        pools[d].append(k+off)
lens = {}
for d in range(1,367):
    if d == 60: 
        continue
    arr = np.unique(pools[d])
    assert arr.min() >= 0 and arr.max() < ndays, (d, arr.min(), arr.max())
    lens[d] = len(arr)
import collections
print("pool size distribution:", collections.Counter(lens.values()))
print("example pool days d=1:", [str(dates[i]) for i in np.unique(pools[1])[:3]], "...", [str(dates[i]) for i in np.unique(pools[1])[-3:]])
print("example pool days d=366:", [str(dates[i]) for i in np.unique(pools[366])[:3]], "...", [str(dates[i]) for i in np.unique(pools[366])[-3:]])
print("d=59 window of 1992:", [str(dates[i]) for i in np.unique(pools[59]) if 1992 <= dates[i].year <= 1992][:14])
print("d=61 window of 1992:", [str(dates[i]) for i in np.unique(pools[61]) if dates[i].year == 1992][:14])
np.save("/tmp/pools.npy", np.array([np.unique(pools[d]) for d in range(1,367)]), allow_pickle=True)
np.save("/tmp/doy.npy", doy)
print("OK pools saved")
