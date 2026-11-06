import xarray as xr
import json
import os

# Check the output files
output_dir = '/work/output'

# Read the report
report_path = os.path.join(output_dir, 'report.json')
with open(report_path, 'r') as f:
    report = json.load(f)
    
print("Report contents:")
print(json.dumps(report, indent=2))

# Read the NetCDF file
nc_path = os.path.join(output_dir, 'mhw_mask.nc')
ds = xr.open_dataset(nc_path)
print("\nNetCDF file contents:")
print(ds)

# Check the shape and some data
print(f"\nMHW mask shape: {ds.mhw.shape}")
print(f"Time dimension: {ds.time.shape}")
print(f"Lat dimension: {ds.lat.shape}")
print(f"Lon dimension: {ds.lon.shape}")

# Show a sample of the data
print(f"Sample MHW data (first 5 days, first 5 lat, first 5 lon):")
print(ds.mhw.isel(time=slice(0,5), lat=slice(0,5), lon=slice(0,5)).values)

print("\nAnalysis completed successfully!")