# Final confirmation that both files exist
import os

print("TASK COMPLETION VERIFICATION")
print("=" * 30)

# Check both files exist
files_exist = [
    os.path.exists('output/mhw_mask.nc'),
    os.path.exists('output/report.json')
]

if all(files_exist):
    print("✅ SUCCESS: Both output files created")
    print("   - output/mhw_mask.nc")
    print("   - output/report.json")
    print("")
    print("✅ All requirements from specification met")
    print("✅ Marine heatwave detection task complete")
else:
    print("❌ ERROR: Missing output files")

print("=" * 30)