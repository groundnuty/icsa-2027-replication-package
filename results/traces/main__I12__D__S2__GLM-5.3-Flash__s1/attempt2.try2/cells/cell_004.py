import xarray as xr, numpy as np, datetime as dt
ds = xr.open_dataset('/work/s2z/sst_s2.nc', engine='h5netcdf')
t = ds.time.values; lat = ds.latitude.values; lon = ds.longitude.values
import sys
print('numpy', np.__version__, 'xarray', xr.__version__)
i0 = np.searchsorted(t, np.datetime64('1991-12-27')); i1 = np.searchsorted(t, np.datetime64('2003-01-05'))
j0 = np.searchsorted(t, np.datetime64('2009-06-01')); j1 = np.searchsorted(t, np.datetime64('2009-08-31'))
print('baseline ext idx', i0, i1, str(t[i0])[:10], str(t[i1])[:10])
print('target idx', j0, j1, str(t[j0])[:10], str(t[j1])[:10])
la = np.where((lat>=56.09)&(lat<=57.29))[0]; lo = np.where((lon>=10.55)&(lon<=11.75))[0]
print('lat idx', la[0], la[-1], 'lon idx', lo[0], lo[-1])
# sample a small block to check units and NaNs
blk = ds.analysed_sst.isel(time=slice(j0, j0+3), latitude=slice(la[0], la[-1]+1), longitude=slice(lo[0], lo[-1]+1)).values
print('sample shape', blk.shape, 'dtype', blk.dtype)
print('sample min/max (finite):', np.nanmin(blk), np.nanmax(blk))
print('finite frac:', np.isfinite(blk).mean())
# how many NaN-only cells in a summer day?
print('cells all-NaN on day1:', np.mean(~np.isfinite(blk[0])))