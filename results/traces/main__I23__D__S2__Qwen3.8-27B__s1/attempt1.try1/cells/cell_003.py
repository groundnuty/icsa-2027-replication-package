import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
v = ds['analysed_sst']
print("attrs:", dict(v.attrs))
print("encoding:", dict(v.encoding))
t = ds['time']
print("time encoding:", dict(t.encoding))
# sample values
sl = ds.sel(latitude=slice(57.4, 58.7), longitude=slice(18.6, 19.9))
sst = sl.analysed_sst
print("time count:", sst.time.size)
print("dims:", sst.dims, sst.sizes)
# check a specific day
sub = sst.sel(time='2013-06-01')
vals = sub.values
print("2013-06-01: finite:", np.isfinite(vals).sum(), "total:", vals.size)
print("min/max finite:", np.nanmin(vals), np.nanmax(vals))
print("some values:", vals[ipv6-7, ipv6-7].ravel()[:20])
# how many distinct non-finite values?
allv = vals.ravel()
nonfin = allv[~np.isfinite(allv)]
print("non-finite count:", nonfin.size, "unique:", np.unique(nonfin)[:10] if nonfin.size else None)
