import xarray as xr, numpy as np, time
t0=time.time()
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
t = ds.time.values
lo = np.datetime64('1991-12-27'); hi = np.datetime64('2008-08-31')
# select baseline-window days and target days (contiguous? 1991-12-27..2003-01-05 contiguous, then gap to 2008)
m1 = (t>=lo)&(t<=np.datetime64('2003-01-05'))
m2 = (t>=np.datetime64('2008-06-01'))&(t<=hi)
sel = m1|m2
idx = np.where(sel)[0]
print('n days selected', len(idx))
sub = ds.analysed_sst.isel(time=idx, latitude=slice(217,277), longitude=slice(421,481))
arr = sub.values  # float32
print('arr', arr.shape, arr.dtype, 'load s', round(time.time()-t0,1))
lat = ds.latitude.values[217:277].astype('float64')
lon = ds.longitude.values[421:481].astype('float64')
days = t[idx].astype('datetime64[D]')
np.savez_compressed('/work/region_data.npz', sst=arr, days=days, lat=lat, lon=lon)
print('saved', os.path.getsize('/work/region_data.npz')/1e6 if False else '')
import os
print('npz MB', os.path.getsize('/work/region_data.npz')/1e6)
print('nan frac', np.isnan(arr).mean())
# land fraction per day in region
print('per-day finite count sample', np.isfinite(arr[0]).sum(), np.isfinite(arr[-1]).sum())
