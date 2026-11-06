# Final verification of output files
import os
print("Final output verification:")
print("- output/mhw_mask.nc:", "Created" if os.path.exists('output/mhw_mask.nc') else "Missing")
print("- output/report.json:", "Created" if os.path.exists('output/report.json') else "Missing")