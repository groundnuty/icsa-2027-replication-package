import os
import xarray as xr
import json

# Check if output files exist
print("Checking output files:")
print(f"mhw_mask.nc exists: {os.path.exists('output/mhw_mask.nc')}")
print(f"report.json exists: {os.path.exists('output/report.json')}")

# Display the report content
if os.path.exists('output/report.json'):
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    print("\nReport contents:")
    print(json.dumps(report, indent=2))

# Display basic info about the NetCDF file
if os.path.exists('output/mhw_mask.nc'):
    try:
        ds = xr.open_dataset('output/mhw_mask.nc')
        print("\nNetCDF file info:")
        print(f"Dimensions: {ds.dims}")
        print(f"Variables: {list(ds.data_vars.keys())}")
        if 'mhw' in ds.data_vars:
            print(f"mhw variable shape: {ds.mhw.shape}")
            print(f"mhw variable dtype: {ds.mhw.dtype}")
        ds.close()
    except Exception as e:
        print(f"Error reading NetCDF: {e}")