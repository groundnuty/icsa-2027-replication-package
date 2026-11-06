# Final confirmation that both files exist
import os

files_exist = [
    os.path.exists('/work/output/mhw_mask.nc'),
    os.path.exists('/work/report.json')
]

if all(files_exist):
    print("✅ TASK COMPLETED SUCCESSFULLY")
    print("Both required files have been generated:")
    print("1. /work/output/mhw_mask.nc")
    print("2. /work/report.json")
else:
    print("❌ Some files are missing")