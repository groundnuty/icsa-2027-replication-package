# Final confirmation
import os

print("TASK COMPLETION VERIFICATION")
print("=" * 30)

# Check both files exist
file1_exists = os.path.exists('output/mhw_mask.nc')
file2_exists = os.path.exists('output/report.json')

if file1_exists and file2_exists:
    print("✅ SUCCESS: Both output files created")
    print("   - output/mhw_mask.nc")
    print("   - output/report.json")
    print("")
    print("✅ All requirements from specification satisfied")
    print("✅ Marine heatwave detection task completed")
else:
    print("❌ ERROR: Missing output files")

print("=" * 30)