import os
import xarray as xr
import json

# Check if output files exist
print("Checking output files...")
if os.path.exists('output/mhw_mask.nc'):
    print("✓ mhw_mask.nc exists")
    # Load and examine the NetCDF file
    try:
        ds = xr.open_dataset('output/mhw_mask.nc')
        print(f"  Dimensions: {ds.dims}")
        print(f"  Variables: {list(ds.data_vars.keys())}")
        print(f"  Shape: {ds.mhw.shape}")
        print(f"  Time range: {ds.time.min().values} to {ds.time.max().values}")
        print(f"  Latitude range: {ds.latitude.min().values} to {ds.latitude.max().values}")
        print(f"  Longitude range: {ds.longitude.min().values} to {ds.longitude.max().values}")
    except Exception as e:
        print(f"  Error reading NetCDF: {e}")
else:
    print("✗ mhw_mask.nc missing")

if os.path.exists('output/report.json'):
    print("✓ report.json exists")
    try:
        with open('output/report.json', 'r') as f:
            report = json.load(f)
        print(f"  Region: {report['region']}")
        print(f"  Baseline period: {report['baseline_analysed']}")
        print(f"  Target period: {report['target_analysed']}")
        print(f"  Events: {len(report['events'])}")
        print(f"  Complete: {report['complete']}")
    except Exception as e:
        print(f"  Error reading JSON: {e}")
else:
    print("✗ report.json missing")

# Also check the file sizes
print("\nFile sizes:")
for filename in ['output/mhw_mask.nc', 'output/report.json']:
    if os.path.exists(filename):
        size = os.path.getsize(filename)
        print(f"  {filename}: {size} bytes")
    else:
        print(f"  {filename}: File not found")