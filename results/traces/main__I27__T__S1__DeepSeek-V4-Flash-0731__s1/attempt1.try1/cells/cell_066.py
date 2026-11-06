
# Final verification that both output files are properly written
import os

for f in ['output/mhw_mask.nc', 'output/report.json']:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f"{f}: {size} bytes")
    else:
        print(f"{f}: MISSING")
