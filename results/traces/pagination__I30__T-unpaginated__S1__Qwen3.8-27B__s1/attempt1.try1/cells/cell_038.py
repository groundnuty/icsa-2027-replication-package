
import xarray, numpy as np, datetime as dt
ds = xarray.open_dataset('/work/output/mhw_mask.nc')
m = ds['mhw'].values
lat_vals = ds['lat'].values
lon_vals = ds['lon'].values
ds.close()

tgt_dates = [dt.date(2010,6,1) + dt.timedelta(days=k) for k in range(92)]
times = np.array([np.datetime64(f'{d.year:04d}-{d.month:02d}-{d.day:02d}') for d in tgt_dates])
print('times[0], times[-1]:', times[0], times[-1])

ds_out = xarray.Dataset(
    data_vars={'mhw': (('time', 'lat', 'lon'), m)},
    coords={'time': ('time', times), 'lat': ('lat', lat_vals), 'lon': ('lon', lon_vals)},
)
ds_out['mhw'].attrs['description'] = '1 where cell is inside a per-cell MHW on that day, 0 otherwise (land/missing cells 0)'
ds_out.to_netcdf('/work/output/mhw_mask.nc', engine='netcdf4')

# verify
ds2 = xarray.open_dataset('/work/output/mhw_mask.nc')
print(ds2)
print('time dtype:', ds2.time.dtype)
print('first/last:', ds2.time.values[0], ds2.time.values[-1])
print('unique mhw:', np.unique(ds2['mhw'].values), 'sum:', int(ds2['mhw'].values.sum()))
ds2.close()
