import xarray as xr, fsspec, numpy as np
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
v = ds['analysed_sst']
print('attrs:', v.attrs)
print('encoding:', {k: v.encoding.get(k) for k in ['dtype','_FillValue','scale_factor','add_offset','units']})
lat = ds.latitude.values; lon = ds.longitude.values
print('lat dtype', lat.dtype, 'lon dtype', lon.dtype)
print('lat[215:222]:', lat[215:222])
print('lon[598:605]:', lon[598:605])
i0 = np.searchsorted(lat, 57.85); i1 = np.searchsorted(lat, 59.05, 'right')
j0 = np.searchsorted(lon, 21.01); j1 = np.searchsorted(lon, 22.21, 'right')
print('indices', i0, i1, j0, j1, 'n', i1-i0, j1-j0)
print('lat range sel', lat[i0], lat[i1-1], 'lon range sel', lon[j0], lon[j1-1])
# check strict comparisons in float64
latd = lat.astype(np.float64); lond = lon.astype(np.float64)
sel_lat = (latd >= 57.85) & (latd <= 59.05); sel_lon = (lond >= 21.01) & (lond <= 22.21)
print('counts', sel_lat.sum(), sel_lon.sum())
print('lat sel vals', latd[sel_lat][:3], latd[sel_lat][-3:])
print('lon sel vals', lond[sel_lon][:3], lond[sel_lon][-3:])
print('time value', ds.time.values, ds.time.encoding)
