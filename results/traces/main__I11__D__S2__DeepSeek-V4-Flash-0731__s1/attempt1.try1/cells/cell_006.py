
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))

# Load target period
target = region.sel(time=slice('2021-06-01', '2021-08-31'))
target_sst = target.analysed_sst.values.astype(np.float64)
print("Target SST shape:", target_sst.shape)

# Load baseline data including window extensions
baseline_ext = region.sel(time=slice('1991-12-27', '2003-01-05'))
baseline_sst = baseline_ext.analysed_sst.values.astype(np.float64)
print("Baseline ext SST shape:", baseline_sst.shape)
print("Baseline ext time range:", baseline_ext.time.values[0], baseline_ext.time.values[-1])
