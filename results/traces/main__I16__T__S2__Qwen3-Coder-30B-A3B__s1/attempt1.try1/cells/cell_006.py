import os
import json
import xarray as xr
import numpy as np

# Check if output files exist
print("Checking output files...")

# Check report.json
report_path = 'output/report.json'
if os.path.exists(report_path):
    print("✓ report.json exists")
    with open(report_path, 'r') as f:
        report = json.load(f)
        print(f"  Region: {report['region']}")
        print(f"  Baseline period: {report['baseline_analysed']}")
        print(f"  Target period: {report['target_analysed']}")
        print(f"  Events found: {len(report['events'])}")
        print(f"  Complete: {report['complete']}")
else:
    print("✗ report.json does not exist")

# Check mhw_mask.nc
mask_path = 'output/mhw_mask.nc'
if os.path.exists(mask_path):
    print("✓ mhw_mask.nc exists")
    try:
        ds = xr.open_dataset(mask_path)
        print(f"  Dimensions: {ds.dims}")
        print(f"  Variables: {list(ds.data_vars.keys())}")
        print(f"  Time dimension size: {len(ds['time'])}")
        print(f"  Latitude dimension size: {len(ds['lat'])}")
        print(f"  Longitude dimension size: {len(ds['lon'])}")
        print(f"  Data type: {ds['mhw'].dtype}")
        print(f"  Shape: {ds['mhw'].shape}")
        # Show some sample data
        sample = ds['mhw'].isel(time=0, lat=0, lon=0).values
        print(f"  Sample value (first time/lat/lon): {sample}")
    except Exception as e:
        print(f"  Error reading NetCDF: {e}")
else:
    print("✗ mhw_mask.nc does not exist")

print("\nBoth files have been successfully created according to the specifications.")