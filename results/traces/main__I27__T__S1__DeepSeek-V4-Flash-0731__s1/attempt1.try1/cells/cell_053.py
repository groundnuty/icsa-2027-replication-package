
import os
os.makedirs('output', exist_ok=True)
print("Output directory created")

# Check if output already has files
if os.path.exists('output/mhw_mask.nc'):
    print("mhw_mask.nc exists")
if os.path.exists('output/report.json'):
    print("report.json exists")
