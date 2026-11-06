import os, numpy as np, xarray as xr
print('numpy', np.__version__, '| xarray', xr.__version__, '| cwd', os.getcwd())
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat64 = ds.latitude.values.astype(np.float64); lon64 = ds.longitude.values.astype(np.float64)
t = ds.time.values

lat_i = np.flatnonzero((lat64 >= 64.39) & (lat64 <= 65.59))
lon_i = np.flatnonzero((lon64 >= 23.41) & (lon64 <= 24.61))
print('lat idx', lat_i[0], '..', lat_i[-1], 'n=', len(lat_i), 'vals', ds.latitude.values[lat_i[0]], ds.latitude.values[lat_i[-1]])
print('lon idx', lon_i[0], '..', lon_i[-1], 'n=', len(lon_i), 'vals', ds.longitude.values[lon_i[0]], ds.longitude.values[lon_i[-1]])
print('neighbours just outside:', ds.latitude.values[lat_i[0]-1], ds.latitude.values[lat_i[-1]+1],
      ds.longitude.values[lon_i[0]-1], ds.longitude.values[lon_i[-1]+1])

for s in ['1991-12-27','1992-01-01','2002-12-31','2003-01-05','2019-06-01','2019-08-31']:
    i = int(np.searchsorted(t, np.datetime64(s)))
    print(s, '-> idx', i, str(t[i])[:10])

n_ext = len(np.arange('1991-12-27','2003-01-06', dtype='datetime64[D]'))
print('extended baseline days:', n_ext)

# hazen quantile support?
try:
    print('hazen ok:', np.quantile(np.arange(1,11.0), 0.9, method='hazen'))
except Exception as e:
    print('no hazen:', e)

# cheap slice check
sl = ds['analysed_sst'].isel(time=slice(13539, 13631), latitude=slice(int(lat_i[0]), int(lat_i[-1])+1), longitude=slice(int(lon_i[0]), int(lon_i[-1])+1))
print('target slice shape:', sl.shape)
print('target first/last time:', str(sl.time.values[0])[:10], str(sl.time.values[-1])[:10])
