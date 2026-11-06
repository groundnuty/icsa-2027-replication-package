import numpy as np, h5py, time as _time
from datetime import date, timedelta

f = h5py.File('/work/sst_s2.nc','r')
tv = f['time'][:].astype(np.int64)
print("t%86400 nonzero count:", np.count_nonzero(tv % 86400))
epoch = date(1981,1,1)
d0 = epoch + timedelta(days=int(tv[0])//86400)
d1 = epoch + timedelta(days=int(tv[-1])//86400)
print("first/last date:", d0, d1)
# date continuity check
ds = np.array([(epoch + timedelta(days=int(s)//86400) - date(1981,1,1)).days for s in tv])
diffs = np.diff(ds)
print("unique diffs:", np.unique(diffs))
def to_date(i): return epoch + timedelta(days=int(tv[i])//86400)
def idx_of(dateobj):
    return int((dateobj - epoch).days)
# find indices of key dates
for dt in [date(1991,12,27), date(2003,1,5), date(2005,6,1), date(2005,8,31)]:
    k = idx_of(dt)
    pos = np.searchsorted(ds, k)
    print(dt, "in file:", pos < len(ds) and ds[pos]==k)

lat = f['latitude'][:]; lon = f['longitude'][:]
print("lat range", lat.min(), lat.max(), "step", np.unique(np.round(np.diff(lat),6))[:5])
print("lon range", lon.min(), lon.max(), "step", np.unique(np.round(np.diff(lon),6))[:5])
latr = np.round(lat.astype(np.float64), 6); lonr = np.round(lon.astype(np.float64), 6)
latmask = (latr >= 59.05) & (latr <= 60.25)
lonmask = (lonr >= 21.25) & (lonr <= 22.45)
ilats = np.where(latmask)[0]; ilons = np.where(lonmask)[0]
print("nlat", len(ilats), ilats[0], ilats[-1], "contiguous:", np.all(np.diff(ilats)==1))
print("nlon", len(ilons), ilons[0], ilons[-1], "contiguous:", np.all(np.diff(ilons)==1))
print("lat sel:", latr[ilats][:3], "...", latr[ilats][-3:])
print("lon sel:", lonr[ilons][:3], "...", lonr[ilons][-3:])
# timing one chunk read
d = f['analysed_sst']
t0=_time.time()
v = d[3000, ilats[0]:ilats[-1]+1, ilons[0]:ilons[-1]+1]
print("one day read:", _time.time()-t0, "s", v.shape, v.dtype, np.isfinite(v).mean())
