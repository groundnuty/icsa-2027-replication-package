import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(p, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

lat = ds.latitude; lon = ds.longitude
la0, la1 = 54.13, 55.33
lo0, lo1 = 14.67, 15.87
# inclusive bounds -> use index-based selection
ii = np.where((lat.values >= la0 - 1e-6) & (lat.values <= la1 + 1e-6))[0]
jj = np.where((lon.values >= lo0 - 1e-6) & (lon.values <= lo1 + 1e-6))[0]
print('lat idx %d..%d n=%d; lon idx %d..%d n=%d' % (ii[0], ii[-1], len(ii), jj[0], jj[-1], len(jj)))
print('lat vals %s..%s; lon vals %s..%s' % (lat.values[ii[0]], lat.values[ii[-1]], lon.values[jj[0]], lon.values[jj[-1]]))

times = ds.time.values
t0 = time.time()
n = 100
buf = np.empty((n, len(ii), len(jj)), dtype=np.float64)
for k in range(n):
    t = times[15000 + k]  # some days in 2023
    buf[k] = ds.analysed_sst.isel(time=15000+k, latitude=ii, longitude=jj).values
dt = time.time() - t0
print('100 days: %.2f s -> %.3f s/day; est 4120 days: %.1f s' % (dt, dt/n, dt/n*4120))
print('sample mean %.2f, nan frac %.3f' % (np.nanmean(buf), np.isnan(buf).mean()))
