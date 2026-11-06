
import numpy as np
import pandas as pd

# Load data
hot = np.load('/tmp/hot.npy')
mhw = np.load('/tmp/mhw.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
target_times = pd.DatetimeIndex(np.load('/tmp/target_times.npy').astype('datetime64[ns]'))

# Find cells where joining occurred
# A cell has joined MHWs if there are MHW days that were non-hot
joined_cells = []
for lat_i, lon_i in np.argwhere(sea_mask):
    hot_series = hot[:, lat_i, lon_i]
    mhw_series = mhw[:, lat_i, lon_i]
    # Check if any MHW day is non-hot
    gap_days = np.where(mhw_series & ~hot_series)[0]
    if len(gap_days) > 0:
        joined_cells.append((lat_i, lon_i, gap_days))

print(f"Cells with joined MHWs: {len(joined_cells)}")
for lat_i, lon_i, gap_days in joined_cells[:5]:
    print(f"  Cell ({lat_i}, {lon_i}): gap days at {[str(target_times[i].date()) for i in gap_days]}")

# Let me verify the joining logic for the first cell
if joined_cells:
    lat_i, lon_i, gap_days = joined_cells[0]
    hot_series = hot[:, lat_i, lon_i]
    mhw_series = mhw[:, lat_i, lon_i]
    print(f"\nCell ({lat_i}, {lon_i}):")
    print("Hot days:", np.where(hot_series)[0])
    print("MHW days:", np.where(mhw_series)[0])
    
    # Show the hot/MHW pattern
    for i in range(len(target_times)):
        h = 'H' if hot_series[i] else '.'
        m = 'M' if mhw_series[i] else '.'
        if h == 'H' or m == 'M':
            print(f"  Day {i} ({target_times[i].date()}): hot={h}, mhw={m}")
