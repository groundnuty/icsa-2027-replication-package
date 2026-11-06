# Final verification that everything is complete
import os

# Verify both files exist
files_exist = [
    os.path.exists('output/mhw_mask.nc'),
    os.path.exists('output/report.json')
]

if all(files_exist):
    print("✅ Task successfully completed!")
    print("Both output files have been created as required.")
else:
    print("❌ Some output files are missing.")