import xarray as xr
import json
import os

# Check if output files exist
print("Checking output files...")

# Check NetCDF file
if os.path.exists('output/mhw_mask.nc'):
    print("✓ mhw_mask.nc exists")
    # Load and inspect
    try:
        ds = xr.open_dataset('output/mhw_mask.nc')
        print(f"  Dimensions: {ds.dims}")
        print(f"  Variables: {list(ds.data_vars.keys())}")
        print(f"  Coordinates: {list(ds.coords.keys())}")
        if 'mhw' in ds.data_vars:
            print(f"  MHW variable shape: {ds.mhw.shape}")
            print(f"  MHW variable dtype: {ds.mhw.dtype}")
    except Exception as e:
        print(f"  Error reading NetCDF: {e}")
else:
    print("✗ mhw_mask.nc missing")

# Check JSON report
if os.path.exists('output/report.json'):
    print("✓ report.json exists")
    try:
        with open('output/report.json', 'r') as f:
            report = json.load(f)
        print(f"  Region: {report['region']}")
        print(f"  Baseline period: {report['baseline_analysed']}")
        print(f"  Target period: {report['target_analysed']}")
        print(f"  Events: {len(report['events'])}")
        print(f"  Complete: {report['complete']}")
    except Exception as e:
        print(f"  Error reading JSON: {e}")
else:
    print("✗ report.json missing")

print("Analysis completed successfully!")