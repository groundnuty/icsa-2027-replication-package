
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Select region
sst_region = ds.analysed_sst.sel(latitude=slice(57.83, 59.03), longitude=slice(17.41, 18.61))
print(sst_region.shape)

# Load baseline period + extensions (1991-12-27 to 2003-01-05)
baseline = sst_region.sel(time=slice('1991-12-27', '2003-01-05'))
print("baseline shape:", baseline.shape)

# Target period
target = sst_region.sel(time=slice('2008-06-01', '2008-08-31'))
print("target shape:", target.shape)

# Convert to numpy
baseline_arr = baseline.values.astype(np.float64)
target_arr = target.values.astype(np.float64)
baseline_time = baseline.time.values
target_time = target.time.values

print("baseline time range:", baseline_time[0], baseline_time[-1], "ndays:", len(baseline_time))
print("target time range:", target_time[0], target_time[-1], "ndays:", len(target_time))
print("lat:", baseline.latitude.values)
print("lon:", baseline.longitude.values)

# Check NaN fraction in baseline
print("baseline NaN fraction:", np.isnan(baseline_arr).mean())
print("target NaN fraction:", np.isnan(target_arr).mean())
