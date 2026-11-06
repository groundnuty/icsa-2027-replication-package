import json
import os

# Read and display the generated report
with open('output/report.json', 'r') as f:
    report = json.load(f)
    
print("Generated Report:")
print(json.dumps(report, indent=2))

# Verify the netCDF file exists
if os.path.exists('output/mhw_mask.nc'):
    print("\nMHW mask file successfully created.")
else:
    print("\nMHW mask file was not created.")