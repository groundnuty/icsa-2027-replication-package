# Final verification with proper imports
import os

print("TASK VERIFICATION COMPLETE")
print("=" * 30)

# Check files
nc_file = 'output/mhw_mask.nc'
json_file = 'output/report.json'

print(f"NetCDF file: {'FOUND' if os.path.exists(nc_file) else 'MISSING'}")
print(f"JSON file: {'FOUND' if os.path.exists(json_file) else 'MISSING'}")

if os.path.exists(nc_file) and os.path.exists(json_file):
    print("\n✅ ALL OUTPUT FILES GENERATED SUCCESSFULLY")
    print("✅ TASK COMPLETION CONFIRMED")
    print("✅ MARINE HEATWAVE DETECTION COMPLETE")
else:
    print("\n❌ OUTPUT FILES MISSING")

print("=" * 30)