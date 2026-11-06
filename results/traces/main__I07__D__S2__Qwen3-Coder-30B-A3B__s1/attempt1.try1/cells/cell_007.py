import xarray as xr
import json
import os

# Check the generated NetCDF file
try:
    mhw_ds = xr.open_dataset('/work/output/mhw_mask.nc')
    print("NetCDF file successfully created:")
    print(mhw_ds)
    print("\nVariable 'mhw' shape:", mhw_ds['mhw'].shape)
    print("Time dimension:", mhw_ds['time'].shape)
    print("Latitude dimension:", mhw_ds['latitude'].shape)
    print("Longitude dimension:", mhw_ds['longitude'].shape)
except Exception as e:
    print(f"Error reading NetCDF: {e}")

# Check the report file
try:
    with open('/work/output/report.json', 'r') as f:
        report = json.load(f)
    print("\nReport file successfully created:")
    print(json.dumps(report, indent=2))
except Exception as e:
    print(f"Error reading report: {e}")