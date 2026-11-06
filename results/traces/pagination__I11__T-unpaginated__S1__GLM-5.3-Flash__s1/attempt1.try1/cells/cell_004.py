import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z'
f = fs.open(p + '/sst_20210601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lat = ds['latitude'].values.astype('float64')
lon = ds['longitude'].values.astype('float64')
dlat = np.diff(lat); dlon = np.diff(lon)
print('lat uniform 0.02:', np.allclose(dlat, 0.02), 'lon uniform 0.02:', np.allclose(dlon, 0.02))
tol = 1e-6
lat_sel = np.flatnonzero((lat >= 55.67 - tol) & (lat <= 56.87 + tol))
lon_sel = np.flatnonzero((lon >= 16.45 - tol) & (lon <= 17.65 + tol))
print('lat idx', lat_sel[0], '..', lat_sel[-1], 'n=', lat_sel.size, 'vals', lat[lat_sel[0]], lat[lat_sel[-1]])
print('lon idx', lon_sel[0], '..', lon_sel[-1], 'n=', lon_sel.size, 'vals', lon[lon_sel[0]], lon[lon_sel[-1]])
i0, i1 = lat_sel[0], lat_sel[-1]; j0, j1 = lon_sel[0], lon_sel[-1]
sst = ds['analysed_sst']
sub = sst[0, i0:i1+1, j0:j1+1]
print('sub shape', sub.shape, 'finite frac', np.isfinite(sub.values).mean())
# check coordinates identical across a few files
for d in ['19820101','19911227','20030105','20210831']:
    g = xr.open_dataset(fs.open(p + f'/sst_{d}.nc','rb'), engine='h5netcdf')
    la = g['latitude'].values; lo = g['longitude'].values
    print(d, 'lat match:', np.array_equal(la, ds['latitude'].values), 'lon match:', np.array_equal(lo, ds['longitude'].values),
          'shape', g['analysed_sst'].shape, 'time', g['time'].values)
    g.close()
