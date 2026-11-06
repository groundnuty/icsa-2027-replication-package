
# Verify output files one final time
import os
print("Final file check:")
print(f"  output/mhw_mask.nc: {os.path.getsize('output/mhw_mask.nc')} bytes")
print(f"  output/report.json: {os.path.getsize('output/report.json')} bytes")
