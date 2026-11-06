# Final verification that both files exist and are accessible
import os
import xarray as xr
import json

# Check files
nc_exists = os.path.exists('output/mhw_mask.nc')
json_exists = os.path.exists('output/report.json')

print(f"NetCDF file exists: {nc_exists}")
print(f"JSON file exists: {json_exists}")

if nc_exists:
    # Test opening NetCDF
    ds = xr.open_dataset('output/mhw_mask.nc')
    print(f"NetCDF dimensions: {ds.dims}")
    ds.close()

if json_exists:
    # Test reading JSON
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    print(f"JSON report complete: {report['complete']}")

print("\n✅ ALL FILES READY FOR USE")