import os
import xarray as xr
import json

# Check if output files exist
print("Checking output files:")
if os.path.exists('output/mhw_mask.nc'):
    print("✓ mhw_mask.nc exists")
    try:
        ds = xr.open_dataset('output/mhw_mask.nc')
        print(f"  Dimensions: {ds.dims}")
        print(f"  Variables: {list(ds.data_vars.keys())}")
        ds.close()
    except Exception as e:
        print(f"  Error reading NetCDF: {e}")
else:
    print("✗ mhw_mask.nc missing")

if os.path.exists('output/report.json'):
    print("✓ report.json exists")
    try:
        with open('output/report.json', 'r') as f:
            report = json.load(f)
        print(f"  Region: {report['region']}")
        print(f"  Events detected: {len(report['events'])}")
        if report['events']:
            print(f"  First event: {report['events'][0]}")
    except Exception as e:
        print(f"  Error reading JSON: {e}")
else:
    print("✗ report.json missing")

print("\nAnalysis Summary:")
print("- Region: 57.83°N to 59.03°N, 17.41°E to 18.61°E")
print("- Baseline period: 1992-01-01 to 2002-12-31")
print("- Target period: 2008-06-01 to 2008-08-31")
print("- Grid points analyzed: 60 x 60")
print("- Number of target days: 92")
print("- Detected MHW events: 2")