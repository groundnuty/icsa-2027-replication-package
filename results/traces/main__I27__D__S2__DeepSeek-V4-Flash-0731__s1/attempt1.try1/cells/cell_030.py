
import os, json
import xarray as xr
import numpy as np

# Final check
print("Files in output/:", os.listdir('output'))

# Read back the NetCDF
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("\nNetCDF summary:")
print(f"  Dimensions: {dict(ds.sizes)}")
print(f"  mhw dtype: {ds.mhw.dtype}")
print(f"  mhw shape: {ds.mhw.shape}")
print(f"  Time: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"  Lat: {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"  Lon: {ds.lon.values[0]} to {ds.lon.values[-1]}")
print(f"  mhw values: {np.unique(ds.mhw.values)}")

# Read back the report
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nReport summary:")
print(f"  Region: {report['region']}")
print(f"  Baseline: {report['baseline_analysed']}")
print(f"  Target: {report['target_analysed']}")
print(f"  Events: {report['events']}")
print(f"  Complete: {report['complete']}")
print(f"  Caveats: '{report['caveats']}'")

# Verify events are in time order
onset_dates = [e['onset'] for e in report['events']]
print(f"\nEvent onsets in order: {onset_dates}")
print(f"Events sorted: {sorted(onset_dates) == onset_dates}")
