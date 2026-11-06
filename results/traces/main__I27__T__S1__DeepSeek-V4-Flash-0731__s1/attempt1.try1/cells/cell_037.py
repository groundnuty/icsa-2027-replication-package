
import xarray as xr
import fsspec
import numpy as np
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
# Check if consecutive
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
