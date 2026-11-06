import numpy as np, xarray as xr
print('numpy', np.__version__, 'xarray', xr.__version__)
try:
    import netCDF4; print('netCDF4', netCDF4.__version__)
except Exception as e: print('no netCDF4', e)
try:
    import h5netcdf; print('h5netcdf', h5netcdf.__version__)
except Exception as e: print('no h5netcdf', e)

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
t = ds.time.values.astype('datetime64[D]')
print('time range', t[0], t[-1], 'n', t.size)
d = np.diff(t).astype(int)
print('daily contiguous:', np.all(d==1), 'dups:', np.sum(d==0))
lat = ds.latitude.values; lon = ds.longitude.values
print('lat', lat[0], lat[-1], 'step', np.unique(np.round(np.diff(lat),6))[:5])
print('lon', lon[0], lon[-1], 'step', np.unique(np.round(np.diff(lon),6))[:5])
latm = (lat >= 57.41) & (lat <= 58.61); lonm = (lon >= 18.69) & (lon <= 19.89)
print('lat cells', latm.sum(), lat[latm][0], lat[latm][-1])
print('lon cells', lonm.sum(), lon[lonm][0], lon[lonm][-1])
# target days present?
tgt = (t >= np.datetime64('2004-06-01')) & (t <= np.datetime64('2004-08-31'))
print('target days present:', tgt.sum())
# check hazen percentile
rng = np.random.default_rng(0)
x = rng.random(137)
a = np.percentile(x, 90, method='hazen')
xs = np.sort(x); N=137; h = N*0.9 - 0.5; lo=int(np.floor(h)); frac=h-lo
manual = xs[lo] + frac*(xs[lo+1]-xs[lo])
print('hazen check:', a, manual, np.isclose(a, manual))