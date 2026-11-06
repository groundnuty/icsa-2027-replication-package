
import os

# Check files exist
for f in ['output/mhw_mask.nc', 'output/report.json']:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f"{f}: exists, size={size} bytes")
    else:
        print(f"{f}: MISSING!")
