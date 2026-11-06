import xarray as xr, numpy as np, json
ds = xr.open_dataset('/work/s2z/sst_s2.nc', engine='h5netcdf')
print('numpy', np.__version__)
print('encoding:', {k: v for k, v in ds.analysed_sst.encoding.items() if k != 'chunksizes'})
print('chunksizes:', ds.analysed_sst.encoding.get('chunksizes'))
# check time continuity
t = ds.time.values
d = np.diff(t).astype('timedelta64[D]').astype(int)
print('time steps unique diffs:', np.unique(d), 'n=', len(t))

# region indices
lat = ds.latitude.values; lon = ds.longitude.values
lat_mask = (lat >= 59.05) & (lat <= 60.25)
lon_mask = (lon >= 21.25) & (lon <= 22.45)
print('nlat', lat_mask.sum(), lat[lat_mask][0], lat[lat_mask][-1])
print('nlon', lon_mask.sum(), lon[lon_mask][0], lon[lon_mask][-1])

# target and baseline windows present?
for a, b in [('2014-06-01','2014-08-31'), ('1991-12-27','2003-01-05')]:
    sel = ds.time.sel(time=slice(a, b))
    print(a, b, len(sel), str(sel.values[0])[:10], str(sel.values[-1])[:10])