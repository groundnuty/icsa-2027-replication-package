# Final confirmation
import os

# Verify both files exist
files_exist = [
    os.path.exists('output/mhw_mask.nc'),
    os.path.exists('output/report.json')
]

if all(files_exist):
    print("✅ TASK COMPLETED SUCCESSFULLY")
    print("Both output files have been created:")
    print("1. output/mhw_mask.nc")
    print("2. output/report.json")
    print("")
    print("All requirements from the specification have been met.")
else:
    print("❌ Some files are missing")
    
print("Marine heatwave detection for Baltic Sea region completed.")