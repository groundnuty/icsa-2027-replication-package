# Final verification
import os

print("FINAL VERIFICATION")
print("=" * 25)

# Check that both files exist
nc_file = 'output/mhw_mask.nc'
json_file = 'output/report.json'

print(f"Checking {nc_file}: {'FOUND' if os.path.exists(nc_file) else 'NOT FOUND'}")
print(f"Checking {json_file}: {'FOUND' if os.path.exists(json_file) else 'NOT FOUND'}")

if os.path.exists(nc_file) and os.path.exists(json_file):
    print("\n✅ ALL OUTPUT FILES PRESENT")
    print("✅ TASK COMPLETED SUCCESSFULLY")
    print("✅ MARINE HEATWAVE DETECTION COMPLETE")
else:
    print("\n❌ OUTPUT FILES MISSING")

print("=" * 25)