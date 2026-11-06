import xarray as xr
import json
import os

# Check the generated NetCDF file
if os.path.exists('output/mhw_mask.nc'):
    print("NetCDF file exists:")
    ds = xr.open_dataset('output/mhw_mask.nc')
    print(ds)
    print("\nVariable info:")
    print(ds['mhw'])
    ds.close()
else:
    print("NetCDF file not found")

# Check the generated JSON report
if os.path.exists('output/report.json'):
    print("\nJSON report exists:")
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    print(json.dumps(report, indent=2))
else:
    print("JSON report not found")