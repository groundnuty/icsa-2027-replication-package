import xarray as xr, numpy as np, time, os

t0=time.time()
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
v = ds['analysed_sst']
print('attrs:', dict(v.attrs))
enc = dict(v.encoding)
print('encoding keys:', {k: enc[k] for k in enc if k in ('dtype','_FillValue','scale_factor','add_offset','chunksizes','preferred_chunks')})

lat_all = ds['latitude'].values
lon_all = ds['longitude'].values
lat64 = lat_all.astype('float64'); lon64 = lon_all.astype('float64')
lat_min, lat_max, lon_min, lon_max = 60.49, 61.69, 17.25, 18.45
lat_idx = np.flatnonzero((lat64 >= lat_min) & (lat64 <= lat_max))
lon_idx = np.flatnonzero((lon64 >= lon_min) & (lon64 <= lon_max))
print('lat_idx', lat_idx[0], lat_idx[-1], 'n', len(lat_idx), 'contig', bool(np.all(np.diff(lat_idx)==1)))
print('lon_idx', lon_idx[0], lon_idx[-1], 'n', len(lon_idx), 'contig', bool(np.all(np.diff(lon_idx)==1)))
print('lat first/last values (f64):', repr(lat64[lat_idx[0]]), repr(lat64[lat_idx[-1]]))
print('lon first/last values (f64):', repr(lon64[lon_idx[0]]), repr(lon64[lon_idx[-1]]))

times = ds['time'].values
i_ext0 = int(np.searchsorted(times, np.datetime64('1991-12-27')))
i_ext1 = int(np.searchsorted(times, np.datetime64('2003-01-05')))
i_t0   = int(np.searchsorted(times, np.datetime64('2010-06-01')))
i_t1   = int(np.searchsorted(times, np.datetime64('2010-08-31')))
print('ext block:', times[i_ext0], times[i_ext1], 'ndays', i_ext1-i_ext0+1)
print('tgt block:', times[i_t0], times[i_t1], 'ndays', i_t1-i_t0+1)

sst_ext = v.isel(time=slice(i_ext0, i_ext1+1), latitude=slice(lat_idx[0], lat_idx[-1]+1), longitude=slice(lon_idx[0], lon_idx[-1]+1)).values
print('ext shape', sst_ext.shape, sst_ext.dtype, 'loaded %.1fs' % (time.time()-t0))
sst_tgt = v.isel(time=slice(i_t0, i_t1+1), latitude=slice(lat_idx[0], lat_idx[-1]+1), longitude=slice(lon_idx[0], lon_idx[-1]+1)).values
print('tgt shape', sst_tgt.shape, sst_tgt.dtype)

np.save('/work/sst_ext.npy', sst_ext)
np.save('/work/sst_tgt.npy', sst_tgt)
np.savez('/work/coords.npz', lat=lat_all[lat_idx], lon=lon_all[lon_idx],
         time_ext=times[i_ext0:i_ext1+1].astype('datetime64[D]'),
         time_tgt=times[i_t0:i_t1+1].astype('datetime64[D]'),
         lat_idx=lat_idx, lon_idx=lon_idx)
print('saved. total %.1fs' % (time.time()-t0))
