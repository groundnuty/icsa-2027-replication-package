import numpy as np, pickle
meta = pickle.load(open("/tmp/target.pkl","rb"))
T = meta["T"]; sea = meta["sea"]
tc = pickle.load(open("/tmp/thrclim.pkl","rb"))
thr_s, clim_s = tc["thr_s"], tc["clim_s"]
lat, lon = meta["lat"], meta["lon"]
slat, slon = meta["slat"], meta["slon"]

sea_flat = sea.reshape(3600)
cs = np.flatnonzero(sea_flat)
Tf = T.reshape(92, 3600)
# target doys
leap_cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy(d): 
    from datetime import date
    return leap_cum[d.month-1]+d.day
from datetime import date, timedelta
d0=date(2017,6,1); dates=[]; cur=d0
while cur<=date(2017,8,31): dates.append(cur); cur+=timedelta(days=1)
doys = np.array([doy(d)-1 for d in dates])

# for 5 sample sea cells: max T over period, thr range over target doys, clim range
for c in cs[::700][:5]:
    l, k = divmod(int(c), 60)
    thr_t = thr_s[doys, c]
    clim_t = clim_s[doys, c]
    print(f"cell ({lat[slat][l]:.2f},{lon[slon][k]:.2f}): T range {Tf[:,c].min():.2f}-{Tf[:,c].max():.2f} K | "
          f"thr range {thr_t.min():.2f}-{thr_t.max():.2f} | clim range {clim_t.min():.2f}-{clim_t.max():.2f} | "
          f"maxT-thrmax = {Tf[:,c].max()-thr_t.max():.2f}")
# also check raw (unsmoothed) threshold for July 15 (doy 197 -> idx 196)
c = cs[1000]
print("sample cell raw thr doy 197:", tc["thr_raw"][196, c], "clim:", tc["clim_raw"][196, c])
print("sample cell T on 2017-07-15 (idx 44):", Tf[44, c])
print("dates idx 44:", dates[44])
