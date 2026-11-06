
import numpy as np
import xarray as xr
import os

# Load the final mask
mhw_mask_flat = np.load('/tmp/mhw_mask_flat_final.npy')  # (92, 3600)
mhw_3d = mhw_mask_flat.reshape(92, 60, 60).astype(np.uint8)
print('MHW mask shape:', mhw_3d.shape)
print('MHW mask dtype:', mhw_3d.dtype)

# Coordinates
region_lat = np.array([56.64, 56.66, 56.68, 56.7, 56.72, 56.739998, 56.76,
                       56.78, 56.8, 56.82, 56.84, 56.86, 56.88, 56.9,
                       56.92, 56.94, 56.96, 56.98, 57., 57.02, 57.04,
                       57.06, 57.079998, 57.1, 57.12, 57.14, 57.16, 57.18,
                       57.2, 57.22, 57.239998, 57.26, 57.28, 57.3, 57.32,
                       57.34, 57.36, 57.38, 57.4, 57.42, 57.44, 57.46,
                       57.48, 57.5, 57.52, 57.54, 57.56, 57.579998, 57.6,
                       57.62, 57.64, 57.66, 57.68, 57.7, 57.72, 57.739998,
                       57.76, 57.78, 57.8, 57.82], dtype=np.float32)

region_lon = np.array([20.24, 20.26, 20.279999, 20.3, 20.32, 20.34, 20.359999,
                       20.38, 20.4, 20.42, 20.439999, 20.46, 20.48, 20.5,
                       20.519999, 20.539999, 20.56, 20.58, 20.599998, 20.619999,
                       20.64, 20.66, 20.679998, 20.699999, 20.72, 20.74,
                       20.759998, 20.779999, 20.8, 20.82, 20.84, 20.859999,
                       20.88, 20.9, 20.92, 20.939999, 20.96, 20.98, 21.,
                       21.019999, 21.039999, 21.06, 21.08, 21.099998, 21.119999,
                       21.14, 21.16, 21.179998, 21.199999, 21.22, 21.24,
                       21.259998, 21.279999, 21.3, 21.32, 21.34, 21.359999,
                       21.38, 21.4, 21.42], dtype=np.float32)

print('Region lat shape:', region_lat.shape)
print('Region lon shape:', region_lon.shape)

# Create time values
from datetime import date, timedelta
import numpy as np

target_dates = []
d = date(2008, 6, 1)
while d <= date(2008, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

times = np.array(target_dates, dtype='datetime64[ns]')
print('Times shape:', times.shape)

# Create xarray dataset
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_3d)
    },
    coords={
        'time': times,
        'lat': region_lat,
        'lon': region_lon
    },
    attrs={
        'description': 'Marine heatwave mask for Baltic Sea region',
        'units': '1 = inside per-cell MHW, 0 = otherwise'
    }
)

# Set variable attributes
ds_out['mhw'].attrs['long_name'] = 'Marine heatwave indicator'
ds_out['mhw'].attrs['units'] = '1 = inside per-cell MHW, 0 = otherwise'

# Write to netCDF
os.makedirs('output', exist_ok=True)
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')

print('Written output/mhw_mask.nc')

# Verify by reading it back
ds_check = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print('\nVerification:')
print('Dimensions:', dict(ds_check.sizes))
print('Variables:', list(ds_check.data_vars))
print('mhw shape:', ds_check['mhw'].shape)
print('mhw dtype:', ds_check['mhw'].dtype)
print('Time range:', ds_check['time'].values[0], 'to', ds_check['time'].values[-1])
print('Lat range:', ds_check['lat'].values[0], 'to', ds_check['lat'].values[-1])
print('Lon range:', ds_check['lon'].values[0], 'to', ds_check['lon'].values[-1])
print('mhw values:', np.unique(ds_check['mhw'].values))
print('mhw sum:', ds_check['mhw'].values.sum())
print('mhw[0].sum:', ds_check['mhw'].values[0].sum())
print('mhw[5].sum:', ds_check['mhw'].values[5].sum())
print('mhw[9].sum:', ds_check['mhw'].values[9].sum())
