# One final check to make sure everything is properly done
import os
import sys

# Check that both files exist
nc_file = 'output/mhw_mask.nc'
json_file = 'output/report.json'

if os.path.exists(nc_file) and os.path.exists(json_file):
    print("SUCCESS: Both required files have been generated.")
    print(f"NetCDF file size: {os.path.getsize(nc_file)} bytes")
    print(f"JSON file size: {os.path.getsize(json_file)} bytes")
    sys.exit(0)
else:
    print("FAILURE: Required files not found")
    sys.exit(1)