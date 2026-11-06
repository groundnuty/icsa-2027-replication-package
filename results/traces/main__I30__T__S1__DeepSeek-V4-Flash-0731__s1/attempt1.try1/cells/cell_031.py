
import numpy as np
import pandas as pd

target_data = np.load('/tmp/target_data.npy').astype(np.float64)
target_times = np.load('/tmp/target_times.npy').astype('datetime64[D]')
sea_mask = np.load('/tmp/sea_mask.npy')
mhw_mask = np.load('/tmp/mhw_mask.npy')

n_time, n_lat, n_lon = mhw_mask.shape

# Check active days
active = np.any(mhw_mask > 0, axis=(1, 2))
for t in range(n_time):
    if active[t]:
        print(f"  Day {t} ({pd.Timestamp(target_times[t]).strftime('%Y-%m-%d')}): {mhw_mask[t].sum()} cells in MHW")
