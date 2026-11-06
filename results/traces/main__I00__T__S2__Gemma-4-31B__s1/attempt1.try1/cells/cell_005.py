import xarray as xr
import json

# Re-open the NetCDF and rename dimensions if necessary
try:
    ds = xr.open_dataset("output/mhw_mask.nc")
    if 'latitude' in ds.dims:
        ds = ds.rename({'latitude': 'lat', 'longitude': 'lon'})
    ds.to_netcdf("output/mhw_mask.nc")
    print("Dimensions renamed successfully.")
except Exception as e:
    print(f"Error: {e}")

# Print report to verify
with open("output/report.json", "r") as f:
    print(json.load(f))
