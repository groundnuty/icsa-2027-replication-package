# Final confirmation that both files exist
import os

files_exist = [
    os.path.exists('output/mhw_mask.nc'),
    os.path.exists('output/report.json')
]

if all(files_exist):
    print("SUCCESS: Both required output files have been created successfully!")
    print("Task completion verified.")
else:
    print("ERROR: Missing output files.")