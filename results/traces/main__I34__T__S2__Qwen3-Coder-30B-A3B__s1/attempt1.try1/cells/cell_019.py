# Final verification that files exist
import os
required_files = ['output/report.json', 'output/mhw_mask.nc', 'output/thresholds.npy', 'output/climatologies.npy']
for file in required_files:
    exists = os.path.exists(file)
    print(f"{file}: {'✓' if exists else '✗'}")