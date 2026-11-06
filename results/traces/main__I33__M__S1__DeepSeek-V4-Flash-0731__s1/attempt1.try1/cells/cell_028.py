
import numpy as np
import os

# Check which files exist
for f in ['threshold_raw.npy', 'climatology_raw.npy', 'threshold_smooth.npy', 'climatology_smooth.npy', 
          'sea_cells.npy', 'target_sst.npy', 'mhw_mask.npy', 'target_dates.npy']:
    path = f'output/{f}'
    if os.path.exists(path):
        print(f"✓ {f} exists, size: {os.path.getsize(path)} bytes")
    else:
        print(f"✗ {f} missing")
