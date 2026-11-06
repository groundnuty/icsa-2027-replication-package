# Final verification that both files exist and are accessible
import os

print("FINAL VERIFICATION")
print("=" * 20)

# Check files exist
nc_file = 'output/mhw_mask.nc'
json_file = 'output/report.json'

print(f"Checking {nc_file}: {'FOUND' if os.path.exists(nc_file) else 'MISSING'}")
print(f"Checking {json_file}: {'FOUND' if os.path.exists(json_file) else 'MISSING'}")

# Verify file sizes
if os.path.exists(nc_file):
    print(f"NetCDF size: {os.path.getsize(nc_file)} bytes")
if os.path.exists(json_file):
    print(f"JSON size: {os.path.getsize(json_file)} bytes")

print("=" * 20)
print("TASK STATUS: COMPLETE")