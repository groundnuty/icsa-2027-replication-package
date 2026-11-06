
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Load target data (2003-06-01 to 2003-08-31)
target_data = ds['analysed_sst'].isel(time=slice(7821, 7913),
                                       latitude=slice(330, 390),
                                       longitude=slice(551, 611)).values
print("Target data shape:", target_data.shape)  # (92, 60, 60)

# Get the time values for target period
target_times = ds.time.values[7821:7913]
print("Target time range:", target_times[0], "to", target_times[-1])
print("Target time count:", len(target_times))

# Check finite per cell across target period
finite_per_cell = np.all(np.isfinite(target_data), axis=0)
print("Sea cells (finite all days):", finite_per_cell.sum())
print("Shape of finite mask:", finite_per_cell.shape)
