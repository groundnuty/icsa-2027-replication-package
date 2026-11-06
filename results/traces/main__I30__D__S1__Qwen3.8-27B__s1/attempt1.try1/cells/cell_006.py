import os, time
from datetime import date, timedelta
import numpy as np
import xarray as xr

def drange(a, b):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)

all_dates = sorted(set(
    [date(1991,12,27)+timedelta(i) for i in range(5)] +
    list(drange(date(1992,1,1), date(2002,12,31))) +
    [date(2003,1,1)+timedelta(i) for i in range(5)] +
    list(drange(date(2010,6,1), date(2010,8,31)))
))
names = ['sst_%s.nc' % d.strftime('%Y%m%d') for d in all_dates]

# region slice from first file
ds0 = xr.open_dataset('/work/data/'+names[0], engine='h5netcdf')
lat_vals = ds0.latitude.values  # float32
lon_vals = ds0.longitude.values
ilat = (260, 320)   # 58.70 .. 59.88
ilong = (485, 545)  # 18.70 .. 19.88
ds0.close()
NLAT = ilat[1]-ilat[0]; NLON = ilong[1]-ilong[0]
print("slice", NLAT, NLON)

A = np.empty((len(all_dates), NLAT, NLON), dtype=np.float64)
t0 = time.time()
for i, nm in enumerate(names):
    p = '/work/data/' + nm
    with xr.open_dataset(p, engine='h5netcdf') as ds:
        v = ds['analysed_sst'].values[0]  # float32 (626,1051)
    A[i] = v[ilat[0]:ilat[1], ilong[0]:ilong[1]].astype(np.float64)
    if i % 1000 == 0:
        print(i, "loaded, %.0fs" % (time.time()-t0), flush=True)
print("loaded all in %.0fs" % (time.time()-t0))

# sanity: finite fraction
fin = np.isfinite(A)
print("overall finite frac:", fin.mean())
print("min/max per-day finite frac:", fin.mean(axis=(1,2)).min(), fin.mean(axis=(1,2)).max())
print("SST range:", np.nanmin(A), np.nanmax(A))

np.savez_compressed('/work/sst_region.npz',
                    A=A,
                    dates=np.array([d.isoformat() for d in all_dates]),
                    lat=lat_vals[ilat[0]:ilat[1]],
                    lon=lon_vals[ilong[0]:ilong[1]])
print("saved /work/sst_region.npz")
