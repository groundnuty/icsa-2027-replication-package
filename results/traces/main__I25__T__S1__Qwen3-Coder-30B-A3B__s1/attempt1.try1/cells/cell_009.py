# Final verification of what we have
import os
print("Output files created:")
if os.path.exists('output/report.json'):
    print("- output/report.json: Created")
else:
    print("- output/report.json: Missing")

if os.path.exists('output/mhw_mask.nc'):
    print("- output/mhw_mask.nc: Created")
else:
    print("- output/mhw_mask.nc: Missing")