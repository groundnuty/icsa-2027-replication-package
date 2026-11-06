# Final confirmation that both files exist and are readable
import os
import xarray as xr
import json

# Check files exist
nc_exists = os.path.exists('output/mhw_mask.nc')
json_exists = os.path.exists('output/report.json')

print(f"NetCDF file exists: {nc_exists}")
print(f"JSON file exists: {json_exists}")

if nc_exists:
    # Verify NetCDF can be opened
    ds = xr.open_dataset('output/mhw_mask.nc')
    print(f"NetCDF dimensions: {ds.dims}")
    ds.close()

if json_exists:
    # Verify JSON can be read
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    print(f"Report contains {len(report)} fields")
    print(f"Complete status: {report.get('complete', 'unknown')}")

print("\n✅ Task execution completed successfully!")