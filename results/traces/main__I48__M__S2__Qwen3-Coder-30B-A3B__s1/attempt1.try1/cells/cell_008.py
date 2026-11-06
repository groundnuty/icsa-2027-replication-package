import xarray as xr
import json

# Check the NetCDF file
print("Checking mhw_mask.nc:")
try:
    ds = xr.open_dataset('output/mhw_mask.nc')
    print(f"Dimensions: {ds.dims}")
    print(f"Variables: {list(ds.data_vars.keys())}")
    print(f"Shape: {ds.mhw.shape}")
    print(f"Data type: {ds.mhw.dtype}")
    print(f"Sample values: {ds.mhw.values.flatten()[:10]}")
except Exception as e:
    print(f"Error reading NetCDF: {e}")

# Check the report file
print("\nChecking report.json:")
try:
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    print(json.dumps(report, indent=2))
except Exception as e:
    print(f"Error reading report: {e}")