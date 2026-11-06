# One final check to ensure everything is properly wrapped up
import os

# Ensure both files exist
nc_file = 'output/mhw_mask.nc'
json_file = 'output/report.json'

if os.path.exists(nc_file) and os.path.exists(json_file):
    print("SUCCESS: Task completed with both output files generated")
    print(f"NetCDF file: {os.path.getsize(nc_file)} bytes")
    print(f"JSON file: {os.path.getsize(json_file)} bytes")
    print("Task execution finished successfully!")
else:
    print("FAILURE: Missing output files")
    exit(1)