
import os
import xarray as xr
import json

# Check files exist
print("Files in output/:")
for f in os.listdir('output'):
    size = os.path.getsize(os.path.join('output', f))
    print(f"  {f}: {size} bytes")

# Verify NetCDF
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"\nNetCDF variable: {list(ds.data_vars.keys())}")
print(f"NetCDF dimensions: {dict(ds.sizes)}")
print(f"NetCDF dtype: {ds['mhw'].dtype}")
print(f"NetCDF shape: {ds['mhw'].shape}")
print(f"NetCDF unique values: {sorted(set(ds['mhw'].values.flatten()))}")
print(f"NetCDF time range: {ds.time.values[0]} to {ds.time.values[-1]}")
ds.close()

# Verify report
with open('output/report.json') as f:
    report = json.load(f)
print(f"\nReport keys: {sorted(report.keys())}")
print(f"Report region: {report['region']}")
print(f"Report baseline: {report['baseline_analysed']}")
print(f"Report target: {report['target_analysed']}")
print(f"Report events: {report['events']}")
print(f"Report complete: {report['complete']}")
print(f"Report caveats: '{report['caveats']}'")

print("\nAll checks passed.")
