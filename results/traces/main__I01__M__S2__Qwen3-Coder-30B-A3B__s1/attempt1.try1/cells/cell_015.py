# Final verification that both files exist and are properly formatted
import os
import xarray as xr
import json

print("Final verification of output files:")

# Verify NetCDF file
nc_path = 'output/mhw_mask.nc'
if os.path.exists(nc_path):
    ds = xr.open_dataset(nc_path)
    print(f"✓ NetCDF file created with shape {ds.mhw.shape}")
    print(f"  Dimensions: {dict(ds.dims)}")
    print(f"  Variable: mhw (dtype: {ds.mhw.dtype})")
else:
    print("✗ NetCDF file missing")

# Verify JSON file  
json_path = 'output/report.json'
if os.path.exists(json_path):
    with open(json_path, 'r') as f:
        report = json.load(f)
    print(f"✓ JSON report created")
    print(f"  Region: {report['region']}")
    print(f"  Baseline period: {report['baseline_analysed']}")
    print(f"  Target period: {report['target_analysed']}")
    print(f"  Events: {len(report['events'])} found")
    print(f"  Complete: {report['complete']}")
else:
    print("✗ JSON report missing")

print("\nTask completed successfully!")