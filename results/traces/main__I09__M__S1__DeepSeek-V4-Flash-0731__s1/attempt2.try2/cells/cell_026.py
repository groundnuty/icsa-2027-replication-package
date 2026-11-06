
import xarray as xr
import numpy as np
import json
from datetime import date, timedelta

# Verify NetCDF output
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== NetCDF Verification ===")
print(f"Dimensions: {dict(ds.dims)}")
print(f"Variables: {list(ds.variables)}")
print(f"mhw dtype: {ds.mhw.dtype}")
print(f"mhw shape: {ds.mhw.shape}")
print(f"Time range: {ds.time.values[0]} to {ds.time.values[-1]}, count={len(ds.time)}")
print(f"Lat range: {ds.lat.values[0]} to {ds.lat.values[-1]}, count={len(ds.lat)}")
print(f"Lon range: {ds.lon.values[0]} to {ds.lon.values[-1]}, count={len(ds.lon)}")
print(f"mhw unique values: {np.unique(ds.mhw.values)}")
print(f"mhw sum: {ds.mhw.values.sum()}")

# Check that the time values are correct
expected_times = []
d = date(2022, 6, 1)
end = date(2022, 8, 31)
while d <= end:
    expected_times.append(np.datetime64(d))
    d += timedelta(days=1)
print(f"Time matches expected: {np.array_equal(ds.time.values, np.array(expected_times))}")

ds.close()

# Verify report
print("\n=== Report Verification ===")
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"Report keys: {list(report.keys())}")
print(f"Region: {report['region']}")
print(f"Baseline: {report['baseline_analysed']}")
print(f"Target: {report['target_analysed']}")
print(f"Events: {report['events']}")
print(f"Complete: {report['complete']}")
print(f"Caveats: {report['caveats']}")

# Check that events match the active days pattern
mhw_mask = np.load('/tmp/mhw_mask.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
active = np.any(mhw_mask & sea_cells[np.newaxis, :, :], axis=(1, 2))

print(f"\n=== Active days pattern ===")
target_dates = []
d = date(2022, 6, 1)
while d <= end:
    target_dates.append(d)
    d += timedelta(days=1)

for t in range(len(active)):
    if active[t]:
        print(f"  {target_dates[t]}: active")
    else:
        print(f"  {target_dates[t]}: -")
