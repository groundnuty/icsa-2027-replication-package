# Final verification that files were created correctly
import os
import json

# Check if output files exist
print("Output files status:")
if os.path.exists("output/report.json"):
    print("✓ report.json created")
    with open("output/report.json", "r") as f:
        report = json.load(f)
        print(f"  Region: {report['region']}")
        print(f"  Events found: {len(report['events'])}")
else:
    print("✗ report.json not found")

if os.path.exists("output/mhw_mask.nc"):
    print("✓ mhw_mask.nc created")
    # Verify it's a proper NetCDF file structure
    import xarray as xr
    try:
        ds = xr.open_dataset("output/mhw_mask.nc")
        print(f"  Dimensions: {ds.dims}")
        print(f"  Variables: {list(ds.data_vars.keys())}")
        print(f"  Coordinates: {list(ds.coords.keys())}")
    except Exception as e:
        print(f"  Error reading NetCDF: {e}")
else:
    print("✗ mhw_mask.nc not found")

print("\nAlgorithm implementation complete!")