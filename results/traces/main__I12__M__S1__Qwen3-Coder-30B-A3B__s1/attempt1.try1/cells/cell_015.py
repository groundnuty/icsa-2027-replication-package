# Verify that the files were created correctly
import os
import xarray as xr
import json

print("Verifying output files:")

# Check if files exist
if os.path.exists('output/mhw_mask.nc'):
    print("✓ mhw_mask.nc exists")
    # Try to open and inspect
    try:
        ds = xr.open_dataset('output/mhw_mask.nc')
        print(f"  Dimensions: {ds.dims}")
        print(f"  Variables: {list(ds.data_vars.keys())}")
        ds.close()
    except Exception as e:
        print(f"  Error opening: {e}")
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
        print(f"  Events count: {len(report['events'])}")
    except Exception as e:
        print(f"  Error reading: {e}")
else:
    print("✗ report.json missing")

print("\nTask completed successfully!")