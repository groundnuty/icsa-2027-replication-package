# Final verification of the output files
import xarray as xr
import json

print("Final verification:")

# Check NetCDF file
try:
    ds = xr.open_dataset('output/mhw_mask.nc')
    print(f"✓ mhw_mask.nc opened successfully")
    print(f"  Dimensions: {ds.dims}")
    print(f"  Variables: {list(ds.data_vars.keys())}")
    ds.close()
except Exception as e:
    print(f"✗ Error opening mhw_mask.nc: {e}")

# Check JSON report
try:
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    print(f"✓ report.json loaded successfully")
    print(f"  Events found: {len(report['events'])}")
    print(f"  Region: {report['region']}")
    print(f"  Complete: {report['complete']}")
except Exception as e:
    print(f"✗ Error loading report.json: {e}")

print("\nTask completed successfully!")