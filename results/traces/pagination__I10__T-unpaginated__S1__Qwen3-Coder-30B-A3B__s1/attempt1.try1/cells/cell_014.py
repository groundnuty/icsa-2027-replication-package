import xarray as xr
import json
import os

# Check the generated files
print("Checking generated files:")

# Check NetCDF file
if os.path.exists('output/mhw_mask.nc'):
    print("✓ NetCDF file exists")
    try:
        ds = xr.open_dataset('output/mhw_mask.nc')
        print(f"  Dimensions: {ds.dims}")
        print(f"  Variables: {list(ds.data_vars.keys())}")
        if 'mhw' in ds.data_vars:
            print(f"  MHW shape: {ds['mhw'].shape}")
            print(f"  MHW dtype: {ds['mhw'].dtype}")
    except Exception as e:
        print(f"  Error reading NetCDF: {e}")
else:
    print("✗ NetCDF file missing")

# Check JSON file
if os.path.exists('output/report.json'):
    print("✓ Report JSON exists")
    try:
        with open('output/report.json', 'r') as f:
            report = json.load(f)
            print(f"  Region: {report.get('region')}")
            print(f"  Baseline period: {report.get('baseline_analysed')}")
            print(f"  Target period: {report.get('target_analysed')}")
            print(f"  Events count: {len(report.get('events', []))}")
            print(f"  Complete: {report.get('complete')}")
    except Exception as e:
        print(f"  Error reading JSON: {e}")
else:
    print("✗ Report JSON missing")