import xarray as xr
import json
import os

# Check the generated NetCDF file
if os.path.exists('output/mhw_mask.nc'):
    print("NetCDF file exists")
    try:
        ds = xr.open_dataset('output/mhw_mask.nc')
        print("NetCDF dimensions:", ds.dims)
        print("NetCDF variables:", list(ds.data_vars.keys()))
        if 'mhw' in ds.data_vars:
            print("MHW variable shape:", ds['mhw'].shape)
            print("MHW variable dtype:", ds['mhw'].dtype)
            print("Sample values:", ds['mhw'].values.flatten()[:10])
    except Exception as e:
        print(f"Error reading NetCDF: {e}")
else:
    print("NetCDF file does not exist")

# Check the generated JSON file
if os.path.exists('output/report.json'):
    print("\nJSON file exists")
    try:
        with open('output/report.json', 'r') as f:
            report = json.load(f)
            print("Report keys:", list(report.keys()))
            print("Region:", report.get('region'))
            print("Baseline period:", report.get('baseline_analysed'))
            print("Target period:", report.get('target_analysed'))
            print("Events count:", len(report.get('events', [])))
    except Exception as e:
        print(f"Error reading JSON: {e}")
else:
    print("JSON file does not exist")