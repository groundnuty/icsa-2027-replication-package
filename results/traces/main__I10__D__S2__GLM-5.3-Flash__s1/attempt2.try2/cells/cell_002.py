import numpy as np, xarray as xr, pandas as pd, json, os

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
sst = ds['analysed_sst']
lat = ds['latitude'].values; lon = ds['longitude'].values; tv = ds['time'].values
print('units:', sst.attrs.get('units'))
print('encoding keys:', {k: sst.encoding.get(k) for k in ('dtype','_FillValue','scale_factor','add_offset','chunksizes','zlib','compressor') if k in sst.encoding})
t64 = pd.DatetimeIndex(tv)
print('time range:', t64[0], t64[-1], 'n=', len(t64))
diffs = np.diff(t64.values)
print('all daily & unique:', bool(np.all(diffs == np.timedelta64(1,'D'))))

# region mask
lat64 = lat.astype(np.float64); lon64 = lon.astype(np.float64)
lat_m = (lat64 >= 55.67) & (lat64 <= 56.87)
lon_m = (lon64 >= 16.45) & (lon64 <= 17.65)
lat_idx = np.where(lat_m)[0]; lon_idx = np.where(lon_m)[0]
print('nlat=%d (%.3f..%.3f)  nlon=%d (%.3f..%.3f)' % (lat_m.sum(), lat[lat_idx][0], lat[lat_idx][-1], lon_m.sum(), lon[lon_idx][0], lon[lon_idx][-1]))

# time windows
ext_m = (t64 >= pd.Timestamp('1991-12-27')) & (t64 <= pd.Timestamp('2003-01-05'))
tgt_m = (t64 >= pd.Timestamp('2005-06-01')) & (t64 <= pd.Timestamp('2005-08-31'))
ext_i = np.where(ext_m)[0]; tgt_i = np.where(tgt_m)[0]
print('ext days:', len(ext_i), t64[ext_i][0].date(), t64[ext_i][-1].date())
print('tgt days:', len(tgt_i), t64[tgt_i][0].date(), t64[tgt_i][-1].date())
print('ext contiguous:', bool(np.all(np.diff(t64[ext_i].values)==np.timedelta64(1,'D'))))
print('tgt contiguous:', bool(np.all(np.diff(t64[tgt_i].values)==np.timedelta64(1,'D'))))

print('numpy', np.__version__, 'xarray', xr.__version__)
import scipy, h5py
print('scipy', scipy.__version__, 'h5py', h5py.__version__)
