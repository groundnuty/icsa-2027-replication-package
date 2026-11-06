
import xarray as xr
import numpy as np

# Read back the mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(ds)
print(f"\nmhw variable shape: {ds['mhw'].shape}")
print(f"mhw dtype: {ds['mhw'].dtype}")
print(f"mhw unique values: {np.unique(ds['mhw'].values)}")
print(f"time: {ds.time.values[0]} to {ds.time.values[-1]}, count={len(ds.time.values)}")
print(f"lat: {ds.lat.values[0]} to {ds.lat.values[-1]}, count={len(ds.lat.values)}")
print(f"lon: {ds.lon.values[0]} to {ds.lon.values[-1]}, count={len(ds.lon.values)}")
ds.close()
