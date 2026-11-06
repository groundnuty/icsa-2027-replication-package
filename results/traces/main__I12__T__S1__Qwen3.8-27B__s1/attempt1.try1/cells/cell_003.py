import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
t0 = time.time()
f = fs.open(f'{base}/sst_19920601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
v = ds['analysed_sst'].values.astype('float64')
lat = ds['latitude'].values.astype('float64')
lon = ds['longitude'].values.astype('float64')
t1 = time.time()
print('read time', t1-t0, 'shape', v.shape, 'dtype', v.dtype)
# check region bounds
m_lat = (lat >= 56.09) & (lat <= 57.29)
m_lon = (lon >= 10.55) & (lon <= 11.75)
print('lat count', m_lat.sum(), 'lon count', m_lon.sum())
print('lats', lat[m_lat][:5], lat[m_lat][-5:])
print('lons', lon[m_lon][:5], lon[m_lon][-5:])
reg = v[:, m_lat][:, :, m_lon]
print('region finite count', np.isfinite(reg).sum(), 'of', reg.size)
print('sample region values', np.nanmean(reg))
ds.close(); f.close()