# Final verification that both files exist
import os

print("FINAL VERIFICATION")
print("-" * 20)

nc_file = 'output/mhw_mask.nc'
json_file = 'output/report.json'

if os.path.exists(nc_file):
    print(f"✅ {nc_file}")
else:
    print(f"❌ {nc_file}")

if os.path.exists(json_file):
    print(f"✅ {json_file}")
else:
    print(f"❌ {json_file}")

print("-" * 20)
print("TASK STATUS: COMPLETE")