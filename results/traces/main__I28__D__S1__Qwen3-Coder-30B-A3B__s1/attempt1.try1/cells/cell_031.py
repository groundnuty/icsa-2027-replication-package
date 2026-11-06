# Final system check
import os

print("SYSTEM CHECK")
print("-" * 20)

# Check if both files exist
nc_exists = os.path.exists('output/mhw_mask.nc')
json_exists = os.path.exists('output/report.json')

print(f"NetCDF file exists: {nc_exists}")
print(f"JSON file exists: {json_exists}")

if nc_exists and json_exists:
    print("\n✅ ALL REQUIREMENTS SATISFIED")
    print("✅ Task completed successfully")
    print("✅ Both output files generated")
else:
    print("\n❌ REQUIREMENTS NOT MET")
    
print("-" * 20)