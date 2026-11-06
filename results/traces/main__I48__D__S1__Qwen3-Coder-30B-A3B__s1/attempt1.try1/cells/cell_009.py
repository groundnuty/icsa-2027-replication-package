import xarray as xr
import json

# Check the generated files
print("Checking mhw_mask.nc...")
try:
    ds = xr.open_dataset('output/mhw_mask.nc')
    print(f"Shape: {ds.mhw.shape}")
    print(f"Dimensions: {ds.dims}")
    print(f"Coordinates: {list(ds.coords.keys())}")
    print(f"Time range: {ds.time.min().values} to {ds.time.max().values}")
    print(f"Lat range: {ds.lat.min().values} to {ds.lat.max().values}")
    print(f"Lon range: {ds.lon.min().values} to {ds.lon.max().values}")
    print("Sample data:")
    print(ds.mhw.values[0:5, 0:3, 0:3])  # First 5 days, first 3 lat/lon
    ds.close()
except Exception as e:
    print(f"Error reading mhw_mask.nc: {e}")

print("\nChecking report.json...")
try:
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    print(json.dumps(report, indent=2))
except Exception as e:
    print(f"Error reading report.json: {e}")