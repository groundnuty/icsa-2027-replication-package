
import xarray as xr
import numpy as np
from datetime import datetime, timezone

# Load data
mhw_mask = np.load('output/mhw_mask.npy')
lat_region = np.load('output/lat_region.npy')
lon_region = np.load('output/lon_region.npy')
target_dates = np.load('output/target_dates.npy')

# Create time array as datetime64
time_coords = target_dates.astype('datetime64[ns]')
print(f"Time coords: {time_coords[0]} to {time_coords[-1]}, shape: {time_coords.shape}")
print(f"MHW mask shape: {mhw_mask.shape}")
print(f"MHW mask dtype: {mhw_mask.dtype}")
print(f"MHW mask values: {np.unique(mhw_mask)}")
print(f"MHW mask sum: {mhw_mask.sum()}")

# Create xarray dataset
ds = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask.astype(np.uint8)),
    },
    coords={
        'time': time_coords,
        'lat': lat_region,
        'lon': lon_region,
    }
)

# Save to NetCDF
ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Saved mhw_mask.nc")

# Verify
ds2 = xr.open_dataset('output/mhw_mask.nc')
print(ds2)
print(f"mhw dtype: {ds2['mhw'].dtype}")
print(f"mhw shape: {ds2['mhw'].shape}")
print(f"mhw sum: {ds2['mhw'].sum().values}")
ds2.close()
