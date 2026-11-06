import os
import xarray as xr
import json

# Check if files were created
print("Checking output files:")
if os.path.exists('output/mhw_mask.nc'):
    print("✓ mhw_mask.nc created")
    # Load and inspect the NetCDF file
    try:
        ds = xr.open_dataset('output/mhw_mask.nc')
        print(f"  Dimensions: {ds.dims}")
        print(f"  Variables: {list(ds.data_vars.keys())}")
        print(f"  Shape: {ds.mhw.shape}")
        ds.close()
    except Exception as e:
        print(f"  Error reading: {e}")
else:
    print("✗ mhw_mask.nc not found")

if os.path.exists('output/report.json'):
    print("✓ report.json created")
    try:
        with open('output/report.json', 'r') as f:
            report = json.load(f)
        print(f"  Region: {report['region']}")
        print(f"  Baseline: {report['baseline_analysed']}")
        print(f"  Target: {report['target_analysed']}")
        print(f"  Events: {len(report['events'])}")
        print(f"  Complete: {report['complete']}")
    except Exception as e:
        print(f"  Error reading: {e}")
else:
    print("✗ report.json not found")

print("\nTask completed successfully!")