import os
import json
import xarray as xr

# Check if the files were created
print("Checking output files:")

# Check report.json
report_path = '/work/report.json'
if os.path.exists(report_path):
    print("✓ report.json exists")
    with open(report_path, 'r') as f:
        report = json.load(f)
    print("Report content:")
    print(json.dumps(report, indent=2))
else:
    print("✗ report.json missing")

# Check mhw_mask.nc
mhw_path = '/work/output/mhw_mask.nc'
if os.path.exists(mhw_path):
    print("✓ mhw_mask.nc exists")
    try:
        ds = xr.open_dataset(mhw_path)
        print("NetCDF structure:")
        print(ds)
        print("Variables:", list(ds.data_vars.keys()))
        print("Dimensions:", dict(ds.dims))
        if 'mhw' in ds.data_vars:
            print("MHW variable shape:", ds['mhw'].shape)
        ds.close()
    except Exception as e:
        print(f"Error reading NetCDF: {e}")
else:
    print("✗ mhw_mask.nc missing")

print("\nDone checking files.")