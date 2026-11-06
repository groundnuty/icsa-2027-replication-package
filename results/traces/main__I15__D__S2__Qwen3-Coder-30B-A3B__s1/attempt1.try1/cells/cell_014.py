import xarray as xr
import json
import os

# Check if output files exist
output_dir = '/work/output'
if os.path.exists(output_dir):
    print("Output directory contents:")
    for file in os.listdir(output_dir):
        print(f"  {file}")
    
    # Check the report file
    report_path = os.path.join(output_dir, 'report.json')
    if os.path.exists(report_path):
        with open(report_path, 'r') as f:
            report = json.load(f)
        print("\nReport content:")
        print(json.dumps(report, indent=2))
    
    # Check the NetCDF file
    nc_path = os.path.join(output_dir, 'mhw_mask.nc')
    if os.path.exists(nc_path):
        print("\nNetCDF file exists.")
        try:
            ds = xr.open_dataset(nc_path)
            print("NetCDF structure:")
            print(ds)
            ds.close()
        except Exception as e:
            print(f"Error opening NetCDF: {e}")
else:
    print("Output directory does not exist.")