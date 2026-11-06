
import xarray as xr
import fsspec
import numpy as np
import pandas as pd
import datetime

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

lat_min, lat_max = 57.83, 59.03
lon_min, lon_max = 17.41, 18.61

region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

baseline = region.sel(time=slice('1991-12-27', '2003-01-05'))
target = region.sel(time=slice('2008-06-01', '2008-08-31'))

print("Baseline time range:", baseline.time.values[0], "to", baseline.time.values[-1], "n=", len(baseline.time))
print("Target time range:", target.time.values[0], "to", target.time.values[-1], "n=", len(target.time))

# Check time continuity
baseline_dates = [pd.Timestamp(t).date() for t in baseline.time.values]
for i in range(1, len(baseline_dates)):
    if (baseline_dates[i] - baseline_dates[i-1]).days != 1:
        print(f"Gap at baseline index {i}: {baseline_dates[i-1]} to {baseline_dates[i]}")
        break
else:
    print("Baseline is continuous daily")

target_dates = [pd.Timestamp(t).date() for t in target.time.values]
for i in range(1, len(target_dates)):
    if (target_dates[i] - target_dates[i-1]).days != 1:
        print(f"Gap at target index {i}: {target_dates[i-1]} to {target_dates[i]}")
        break
else:
    print("Target is continuous daily")

# Store the data
baseline_data = baseline.analysed_sst.values.astype(np.float64)
target_data = target.analysed_sst.values.astype(np.float64)
baseline_times = pd.DatetimeIndex(baseline.time.values)
target_times = pd.DatetimeIndex(target.time.values)

print(f"Baseline data shape: {baseline_data.shape}")
print(f"Target data shape: {target_data.shape}")

# Save for later use
np.save('/tmp/baseline_data.npy', baseline_data)
np.save('/tmp/target_data.npy', target_data)
np.save('/tmp/baseline_times.npy', baseline_times.values.astype('datetime64[D]'))
np.save('/tmp/target_times.npy', target_times.values.astype('datetime64[D]'))
# Save coordinates
np.save('/tmp/lat_values.npy', region.latitude.values)
np.save('/tmp/lon_values.npy', region.longitude.values)
print("Data saved")
