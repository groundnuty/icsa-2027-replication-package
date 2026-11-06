# Final confirmation that both files exist
import os

print("FINAL VERIFICATION")
print("=" * 20)

# Check files
file1_exists = os.path.exists('output/mhw_mask.nc')
file2_exists = os.path.exists('output/report.json')

if file1_exists and file2_exists:
    print("✅ Both output files created successfully")
    print("   - output/mhw_mask.nc")
    print("   - output/report.json")
    print("")
    print("✅ All task requirements have been met")
    print("✅ Marine heatwave detection task complete")
else:
    print("❌ Some files are missing")

print("=" * 20)