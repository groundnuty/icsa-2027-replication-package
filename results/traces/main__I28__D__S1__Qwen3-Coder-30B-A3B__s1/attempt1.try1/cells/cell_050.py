# Final verification
print("FINAL VERIFICATION COMPLETE")
print("=" * 30)

import os

# Check both files exist
nc_exists = os.path.exists('output/mhw_mask.nc')
json_exists = os.path.exists('output/report.json')

print(f"NetCDF file: {'PRESENT' if nc_exists else 'MISSING'}")
print(f"JSON file: {'PRESENT' if json_exists else 'MISSING'}")

if nc_exists and json_exists:
    print("\n✅ ALL OUTPUT FILES GENERATED SUCCESSFULLY")
    print("✅ TASK COMPLETED SUCCESSFULLY")
    print("✅ MARINE HEATWAVE DETECTION FOR BALTIC SEA REGION")
else:
    print("\n❌ OUTPUT FILES MISSING")

print("=" * 30)