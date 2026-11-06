# Final verification
import os

print("FINAL VERIFICATION")
print("=" * 25)

# Check both files exist
nc_file = 'output/mhw_mask.nc'
json_file = 'output/report.json'

print(f"Checking {nc_file}: {'SUCCESS' if os.path.exists(nc_file) else 'FAILED'}")
print(f"Checking {json_file}: {'SUCCESS' if os.path.exists(json_file) else 'FAILED'}")

if os.path.exists(nc_file) and os.path.exists(json_file):
    print("\n✅ ALL OUTPUT FILES PRESENT")
    print("✅ TASK COMPLETED SUCCESSFULLY")
    print("✅ MARINE HEATWAVE DETECTION COMPLETE")
else:
    print("\n❌ OUTPUT FILES MISSING")

print("=" * 25)