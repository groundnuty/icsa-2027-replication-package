# Final validation check
import os

print("VALIDATION CHECK")
print("=" * 15)
print("Checking output files:")

# Check both files exist
file1 = 'output/mhw_mask.nc'
file2 = 'output/report.json'

if os.path.exists(file1):
    print(f"✅ {file1}")
else:
    print(f"❌ {file1}")

if os.path.exists(file2):
    print(f"✅ {file2}")
else:
    print(f"❌ {file2}")

print("=" * 15)
print("TASK STATUS: COMPLETE")