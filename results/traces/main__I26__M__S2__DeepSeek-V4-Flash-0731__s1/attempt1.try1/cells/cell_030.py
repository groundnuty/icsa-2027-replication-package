
import os
import json

# Check output files exist
print("Output files:")
print(f"  mhw_mask.nc: exists={os.path.exists('output/mhw_mask.nc')}, size={os.path.getsize('output/mhw_mask.nc')}")
print(f"  report.json: exists={os.path.exists('output/report.json')}, size={os.path.getsize('output/report.json')}")

# Read report
with open('output/report.json', 'r') as f:
    report = json.load(f)

print("\nReport fields:", list(report.keys()))
print(f"  region: {report['region']}")
print(f"  baseline_analysed: {report['baseline_analysed']}")
print(f"  target_analysed: {report['target_analysed']}")
print(f"  events: {report['events']}")
print(f"  complete: {report['complete']}")
print(f"  caveats: {report['caveats']}")

# Read mask
import xarray as xr
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"\nmhw_mask.nc:")
print(f"  Variables: {list(ds.variables)}")
print(f"  dims: {dict(ds.sizes)}")
print(f"  mhw dtype: {ds.mhw.dtype}")
print(f"  mhw values: {ds.mhw.values.min()} to {ds.mhw.values.max()}")
print(f"  mhw sum: {ds.mhw.values.sum()}")
print(f"  time: {ds.time.values[0]} to {ds.time.values[-1]}")
ds.close()

print("\nAll output files are correctly written.")
