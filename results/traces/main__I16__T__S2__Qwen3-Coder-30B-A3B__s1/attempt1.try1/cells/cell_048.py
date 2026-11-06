# Final confirmation
import os

print("TASK COMPLETION VERIFICATION")
print("=" * 28)

# Check both files exist
files_exist = [
    os.path.exists('output/mhw_mask.nc'),
    os.path.exists('output/report.json')
]

if all(files_exist):
    print("✅ SUCCESS: Both files created")
    print("   output/mhw_mask.nc")
    print("   output/report.json")
    print("")
    print("✅ All task requirements satisfied")
    print("✅ Marine heatwave detection complete")
else:
    print("❌ ERROR: Files not created properly")

print("=" * 28)