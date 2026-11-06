
import numpy as np
import xarray as xr
import pandas as pd
import json

# Verify final output files
print("=== Final Output Verification ===\n")

# 1. Check mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("mhw_mask.nc:")
print(f"  Dimensions: {dict(ds.sizes)}")
print(f"  Variable dtype: {ds.mhw.dtype}")
print(f"  Variable shape: {ds.mhw.shape}")
print(f"  Unique values: {np.unique(ds.mhw.values)}")
print(f"  Total ones: {ds.mhw.values.sum()}")
print(f"  Time range: {str(ds.time.values[0])[:10]} to {str(ds.time.values[-1])[:10]}")
print(f"  Lat range: {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"  Lon range: {ds.lon.values[0]} to {ds.lon.values[-1]}")

# Check that land cells (non-sea) are all 0
target = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf').sel(
    latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65),
    time=slice('2021-06-01', '2021-08-31'))
target_sst = target.analysed_sst.values.astype(np.float64)
sea_mask = np.all(np.isfinite(target_sst), axis=0)
non_sea = ~sea_mask
mhw_vals = ds.mhw.values  # (time, lat, lon)
non_sea_mhw = mhw_vals[:, non_sea]
print(f"  Non-sea cells MHW values: {np.unique(non_sea_mhw)}")
print(f"  Non-sea cells count: {non_sea.sum()}")

# 2. Check report.json
print("\nreport.json:")
with open('output/report.json') as f:
    report = json.load(f)
print(f"  region: {report['region']}")
print(f"  baseline_analysed: {report['baseline_analysed']}")
print(f"  target_analysed: {report['target_analysed']}")
print(f"  events: {report['events']}")
print(f"  complete: {report['complete']}")
print(f"  caveats: {report['caveats']}")

# 3. Verify events match active days
active = ds.mhw.values.sum(axis=(1,2)) > 0
print(f"\nActive days: {active.sum()}")
# Find maximal runs of active days
runs = []
t = 0
while t < len(active):
    if active[t]:
        start = t
        while t < len(active) and active[t]:
            t += 1
        runs.append((start, t-1))
    else:
        t += 1
print(f"Regional event runs: {runs}")

# Verify events in report match
target_dates = pd.to_datetime(target.time.values).date
for start, end in runs:
    print(f"  Event: {target_dates[start]} to {target_dates[end]}")
    assert str(target_dates[start]) == report['events'][0]['onset']
    assert str(target_dates[end]) == report['events'][0]['end']
print("  ✓ Events match report")
