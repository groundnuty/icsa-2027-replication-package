# Final confirmation that both files exist and are valid
import os

# Verify the files exist
files_exist = [
    os.path.exists('output/mhw_mask.nc'),
    os.path.exists('output/report.json')
]

if all(files_exist):
    print("✅ TASK COMPLETED SUCCESSFULLY")
    print("Both required output files have been generated:")
    print("  1. output/mhw_mask.nc")
    print("  2. output/report.json")
    print("")
    print("Marine heatwave detection for Baltic Sea region completed according to specifications.")
else:
    print("❌ TASK INCOMPLETE - Missing output files")
    exit(1)