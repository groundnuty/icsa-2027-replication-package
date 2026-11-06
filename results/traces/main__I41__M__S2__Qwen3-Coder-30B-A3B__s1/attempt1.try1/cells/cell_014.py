# Final verification that our output files were created correctly
import os
import xarray as xr
import json

print("Verifying output files:")

# Check if mhw_mask.nc exists and can be opened
if os.path.exists('output/mhw_mask.nc'):
    try:
        ds = xr.open_dataset('output/mhw_mask.nc')
        print(f"✓ mhw_mask.nc created successfully")
        print(f"  Dimensions: {ds.dims}")
        print(f"  Variables: {list(ds.data_vars.keys())}")
        print(f"  Shape: {ds.mhw.shape}")
    except Exception as e:
        print(f"✗ Error reading mhw_mask.nc: {e}")
else:
    print("✗ mhw_mask.nc not found")

# Check if report.json exists and can be read
if os.path.exists('output/report.json'):
    try:
        with open('output/report.json', 'r') as f:
            report = json.load(f)
        print(f"✓ report.json created successfully")
        print(f"  Region: {report['region']}")
        print(f"  Events: {len(report['events'])} events")
        print(f"  Complete: {report['complete']}")
    except Exception as e:
        print(f"✗ Error reading report.json: {e}")
else:
    print("✗ report.json not found")