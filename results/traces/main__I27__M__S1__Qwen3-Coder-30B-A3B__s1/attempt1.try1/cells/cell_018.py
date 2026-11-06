# Final confirmation that both files exist
import os

files_exist = [
    os.path.exists('output/mhw_mask.nc'),
    os.path.exists('output/report.json')
]

if all(files_exist):
    print("SUCCESS: Both required files have been created successfully.")
    print("- output/mhw_mask.nc")
    print("- output/report.json")
else:
    print("ERROR: One or more required files were not created.")
    
print("\nMarine heatwave analysis completed for Baltic Sea region.")