import xarray as xr, numpy as np, time
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values.astype(np.float64)
lon = ds.longitude.values.astype(np.float64)
lat_idx = np.where((lat >= 58.69) & (lat <= 59.89))[0]
lon_idx = np.where((lon >= 18.69) & (lon <= 19.89))[0]
print('lat_idx:', lat_idx[0], lat_idx[-1], 'n=', len(lat_idx))
print('lon_idx:', lon_idx[0], lon_idx[-1], 'n=', len(lon_idx))
t0=time.time()
test = ds.analysed_sst.isel(latitude=lat_idx, longitude=lon_idx).sel(time=slice('1992-06-01','1992-06-30')).load()
print('30 days read in', time.time()-t0, 's; shape', test.shape)
# exact time coverage check
times = ds.time.values.astype('datetime64[D]')
targ = times[(times>=np.datetime64('2010-06-01'))&(times<=np.datetime64('2010-08-31'))]
print('n target days in ds:', len(targ), targ[0], targ[-1])
base_range = times[(times>=np.datetime64('1991-12-27'))&(times<=np.datetime64('2003-01-05'))]
print('n baseline-range days in ds:', len(base_range), base_range[0], base_range[-1])
# continuity
d = np.diff(base_range.astype(int))
print('baseline gaps:', set(d.tolist()))
print('target gaps:', set(np.diff(targ.astype(int)).tolist()))
