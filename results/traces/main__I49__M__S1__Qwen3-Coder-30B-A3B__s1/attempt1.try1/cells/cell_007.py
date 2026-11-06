import json
import xarray as xr
import numpy as np

# Read the report file
with open('output/report.json', 'r') as f:
    report = json.load(f)

print("Report contents:")
print(json.dumps(report, indent=2))

# Read the NetCDF file to verify its structure
try:
    ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
    print("\nNetCDF file structure:")
    print(ds)
    print("\nMHW data shape:", ds['mhw'].shape)
    print("Time dimension:", ds['time'].values)
    print("Lat dimension:", ds['lat'].values[:5], "...")  # Show first 5 values
    print("Lon dimension:", ds['lon'].values[:5], "...")  # Show first 5 values
    print("Sample MHW data (first 3 days):")
    print(ds['mhw'][:3, :, :].values)
    ds.close()
except Exception as e:
    print(f"Error reading NetCDF: {e}")