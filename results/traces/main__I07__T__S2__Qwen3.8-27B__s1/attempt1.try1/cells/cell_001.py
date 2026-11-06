
import fsspec, xarray as xr, numpy as np, time
t0 = time.time()
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print("open time: %.1fs" % (time.time()-t0))
print("dims:", dict(ds.dims))
print("coords:", list(ds.coords))
print("data_vars:", list(ds.data_vars))
t = ds['time']
print("time dtype:", t.dtype, "attrs:", t.attrs)
import pandas as pd
tv = pd.DatetimeIndex(t.values)
print("time range:", tv[0], "->", tv[-1], " n =", len(tv))
diffs = np.diff(tv.asi8)/86400000000000
print("non-1-day steps:", int(np.sum(diffs != 1)), " gaps>1:", int(np.sum(diffs>1)))
lat = ds['lat']; lon = ds['lon']
print("lat:", lat.dtype, len(lat), "first/last:", float(lat.values[0]), float(lat.values[-1]), "monotone inc:", bool((np.diff(lat.values)>0).all()))
print("lon:", lon.dtype, len(lon), "first/last:", float(lon.values[0]), float(lon.values[-1]), "monotone inc:", bool((np.diff(lon.values)>0).all()))
for v in ds.data_vars:
    var = ds[v]
    print("var:", v, var.dims, var.dtype, {k: var.attrs.get(k) for k in ('units','standard_name','_FillValue','missing_value') if k in var.attrs})
ds.close()
f.close()
print("total: %.1fs" % (time.time()-t0))
