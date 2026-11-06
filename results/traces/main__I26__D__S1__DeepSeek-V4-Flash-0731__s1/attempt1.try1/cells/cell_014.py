import xarray as xr
import numpy as np

# Use dask for chunked loading
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf', chunks={'time': 500})

# Select region
region = ds.sel(latitude=slice(57.83, 59.03), longitude=slice(17.41, 18.61))

# Extract baseline data
baseline = region.analysed_sst.sel(time=slice('1991-12-27', '2003-01-05'))
baseline_data = baseline.compute()
print("Baseline shape:", baseline_data.shape)
print("Baseline dtype:", baseline_data.dtype)
print("Baseline non-NaN count:", np.sum(~np.isnan(baseline_data.values)))
