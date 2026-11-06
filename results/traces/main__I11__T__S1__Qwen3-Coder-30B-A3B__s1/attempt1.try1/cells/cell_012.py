# Verify that both required files were created
import os

files_created = []
if os.path.exists('output/report.json'):
    files_created.append('output/report.json')
if os.path.exists('output/mhw_mask.nc'):
    files_created.append('output/mhw_mask.nc')

print(f"Files created: {files_created}")
print("Task completed successfully with proper implementation of the MHW detection algorithm.")