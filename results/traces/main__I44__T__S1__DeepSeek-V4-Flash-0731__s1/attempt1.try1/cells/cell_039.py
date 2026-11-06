import os

# Check output files exist
print("Files in output directory:")
for f in os.listdir('output'):
    path = os.path.join('output', f)
    size = os.path.getsize(path)
    print(f"  {f}: {size} bytes")

# Check mhw_mask.nc
import xarray as xr
ds = xr.open_dataset('output/mhw_mask.nc')
print("\nmhw_mask.nc:")
print(f"  Shape: {ds['mhw'].shape}")
print(f"  Dtype: {ds['mhw'].dtype}")
print(f"  Sum: {ds['mhw'].sum().values}")
print(f"  Time: {ds['time'].values[0]} to {ds['time'].values[-1]}")
print(f"  Lat: {ds['lat'].values[0]} to {ds['lat'].values[-1]}")
print(f"  Lon: {ds['lon'].values[0]} to {ds['lon'].values[-1]}")

# Check report.json
import json
with open('output/report.json') as f:
    report = json.load(f)
print("\nreport.json:")
print(json.dumps(report, indent=2))
