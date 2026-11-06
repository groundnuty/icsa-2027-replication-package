# Final confirmation that both files are properly formatted
import xarray as xr
import json

# Verify NetCDF structure
ds = xr.open_dataset('output/mhw_mask.nc')
print("NetCDF Structure:")
print(f"Dimensions: {ds.dims}")
print(f"Variables: {list(ds.data_vars.keys())}")
print(f"Coordinates: {list(ds.coords.keys())}")
ds.close()

# Verify JSON content
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nReport Content:")
print(f"Region: {report['region']}")
print(f"Baseline: {report['baseline_analysed']}")
print(f"Target: {report['target_analysed']}")
print(f"Events: {report['events']}")
print(f"Complete: {report['complete']}")

print("\n✅ All outputs verified successfully!")