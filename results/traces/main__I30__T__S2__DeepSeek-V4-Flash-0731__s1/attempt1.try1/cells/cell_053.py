
import numpy as np
import pandas as pd

# Load data
mhw_mask = np.load('/tmp/mhw_mask.npy')
hot = np.load('/tmp/hot.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
target_time = np.load('/tmp/target_time.npy')

target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]
n_time, n_lat, n_lon = mhw_mask.shape

# Find cells where mhw has True but hot has False (gap days in joined MHW)
# This indicates a gap was filled by the join operation
found = False
for lat_i in range(n_lat):
    for lon_j in range(n_lon):
        if sea_mask[lat_i, lon_j]:
            # Find days where mhw=True but hot=False
            gap_days = np.where(mhw_mask[:, lat_i, lon_j] & ~hot[:, lat_i, lon_j])[0]
            if len(gap_days) > 0:
                print(f"Cell ({lat_i}, {lon_j}) has gap days in MHW at indices: {gap_days}")
                for t in gap_days:
                    print(f"  {target_dates[t].strftime('%Y-%m-%d')}")
                found = True
                break
    if found:
        break

if not found:
    print("No cells with gap days in joined MHWs found")
