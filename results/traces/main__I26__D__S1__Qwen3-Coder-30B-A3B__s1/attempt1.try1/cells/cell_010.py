# Final status check
import os

files_created = [
    os.path.exists('output/mhw_mask.nc'),
    os.path.exists('output/report.json')
]

if all(files_created):
    print("✅ Both required files have been successfully created")
    print("✅ Task completed successfully!")
else:
    print("❌ Some files were not created properly")