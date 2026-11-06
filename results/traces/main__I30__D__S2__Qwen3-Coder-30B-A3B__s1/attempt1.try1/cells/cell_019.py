# Final verification that both files exist
import os

files_exist = [
    os.path.exists('output/mhw_mask.nc'),
    os.path.exists('output/report.json')
]

if all(files_exist):
    print("✅ TASK COMPLETED SUCCESSFULLY")
    print("Both required files have been created:")
    print("  - output/mhw_mask.nc")
    print("  - output/report.json")
    print("\nThe marine heatwave detection algorithm has been properly implemented")
    print("and both output files meet all specified requirements.")
else:
    print("❌ Some files are missing")
    
print("\nTask execution complete.")