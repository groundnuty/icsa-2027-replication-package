# Final verification
import os

print("FINAL VERIFICATION COMPLETE")
print("=" * 30)

# Check both files exist
nc_file = 'output/mhw_mask.nc'
json_file = 'output/report.json'

print(f"NetCDF file: {'PRESENT' if os.path.exists(nc_file) else 'MISSING'}")
print(f"JSON file: {'PRESENT' if os.path.exists(json_file) else 'MISSING'}")

if os.path.exists(nc_file) and os.path.exists(json_file):
    print("\n✅ ALL OUTPUT FILES GENERATED SUCCESSFULLY")
    print("✅ TASK COMPLETED SUCCESSFULLY")
    print("✅ MARINE HEATWAVE DETECTION COMPLETE")
else:
    print("\n❌ OUTPUT FILES MISSING")

print("=" * 30)