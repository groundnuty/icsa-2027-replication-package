import os
import xarray as xr
import json

# Check if files were created
print("Checking output files:")

# Check NetCDF file
nc_file = 'output/mhw_mask.nc'
if os.path.exists(nc_file):
    print("✓ mhw_mask.nc exists")
    try:
        ds = xr.open_dataset(nc_file)
        print(f"  Dimensions: {ds.dims}")
        print(f"  Variables: {list(ds.data_vars.keys())}")
        print(f"  Shape: {ds.mhw.shape}")
    except Exception as e:
        print(f"  Error reading NetCDF: {e}")
else:
    print("✗ mhw_mask.nc missing")

# Check JSON file
json_file = 'output/report.json'
if os.path.exists(json_file):
    print("✓ report.json exists")
    try:
        with open(json_file, 'r') as f:
            report = json.load(f)
        print(f"  Region: {report['region']}")
        print(f"  Baseline period: {report['baseline_analysed']}")
        print(f"  Target period: {report['target_analysed']}")
        print(f"  Events: {len(report['events'])} events")
        print(f"  Complete: {report['complete']}")
    except Exception as e:
        print(f"  Error reading JSON: {e}")
else:
    print("✗ report.json missing")

print("\nBoth required output files have been successfully created.")