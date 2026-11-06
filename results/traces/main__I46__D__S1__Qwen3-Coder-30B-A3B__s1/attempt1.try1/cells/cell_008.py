# Verify the generated files exist
import os
print("Generated files:")
print("-" * 30)
if os.path.exists('output/mhw_mask.nc'):
    print("✓ output/mhw_mask.nc: Created successfully")
else:
    print("✗ output/mhw_mask.nc: Missing")

if os.path.exists('output/report.json'):
    print("✓ output/report.json: Created successfully")
else:
    print("✗ output/report.json: Missing")

# Show basic info about the generated files
if os.path.exists('output/mhw_mask.nc'):
    import xarray as xr
    ds = xr.open_dataset('output/mhw_mask.nc')
    print(f"NetCDF dimensions: {ds.dims}")
    print(f"NetCDF variables: {list(ds.data_vars.keys())}")
    ds.close()

if os.path.exists('output/report.json'):
    import json
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    print(f"Report events: {len(report['events'])}")
    print(f"Report region: {report['region']}")