import xarray as xr
import json
import os

# Check the NetCDF file
if os.path.exists('output/mhw_mask.nc'):
    ds = xr.open_dataset('output/mhw_mask.nc')
    print("NetCDF file contents:")
    print(ds)
    print("\nVariable 'mhw' shape:", ds.mhw.shape)
    print("Variable 'mhw' data type:", ds.mhw.dtype)
    print("Sample data (first few time steps):")
    print(ds.mhw.isel(time=slice(0, 5)).values)
else:
    print("NetCDF file was not created.")

# Check the JSON report
if os.path.exists('output/report.json'):
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    print("\nReport contents:")
    print(json.dumps(report, indent=2))
else:
    print("Report file was not created.")