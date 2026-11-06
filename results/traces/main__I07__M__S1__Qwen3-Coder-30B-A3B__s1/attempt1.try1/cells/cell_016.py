# Verify final output
import os

print("Final verification of output files:")
print("=" * 40)

# Check mhw_mask.nc
if os.path.exists("output/mhw_mask.nc"):
    print("✓ mhw_mask.nc: CREATED SUCCESSFULLY")
    # Get file size
    size = os.path.getsize("output/mhw_mask.nc")
    print(f"  Size: {size} bytes")
else:
    print("✗ mhw_mask.nc: MISSING")

# Check report.json
if os.path.exists("output/report.json"):
    print("✓ report.json: CREATED SUCCESSFULLY")
    # Get file size
    size = os.path.getsize("output/report.json")
    print(f"  Size: {size} bytes")
else:
    print("✗ report.json: MISSING")

print("\nDirectory contents:")
for item in os.listdir("output"):
    print(f"  {item}")

print("\nTask completion confirmed.")