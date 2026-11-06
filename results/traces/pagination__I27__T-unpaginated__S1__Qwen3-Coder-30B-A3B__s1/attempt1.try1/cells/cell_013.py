# Final cleanup and confirmation
import os

# Verify files exist
files_exist = [
    os.path.exists('output/mhw_mask.nc'),
    os.path.exists('output/report.json')
]

if all(files_exist):
    print("✅ Task completed successfully!")
    print("Files generated:")
    print("  - output/mhw_mask.nc")
    print("  - output/report.json")
else:
    print("❌ Some files were not created properly")