import xarray as xr
import json

# Check the NetCDF file
try:
    ds = xr.open_dataset('output/mhw_mask.nc')
    print("NetCDF file structure:")
    print(ds)
    print("\nMHW variable info:")
    print(ds['mhw'])
    print("\nShape:", ds['mhw'].shape)
    print("Dimensions:", ds['mhw'].dims)
    print("Coordinate ranges:")
    print("Time:", ds['time'].min().values, "to", ds['time'].max().values)
    print("Latitude:", ds['lat'].min().values, "to", ds['lat'].max().values)
    print("Longitude:", ds['lon'].min().values, "to", ds['lon'].max().values)
except Exception as e:
    print(f"Error reading NetCDF: {e}")

# Check the report file
try:
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    print("\nReport content:")
    print(json.dumps(report, indent=2))
except Exception as e:
    print(f"Error reading report: {e}")