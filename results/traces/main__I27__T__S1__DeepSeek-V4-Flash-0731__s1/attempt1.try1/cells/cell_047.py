
import numpy as np
import pandas as pd

# Load data
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
target_data = np.load('/tmp/target_data.npy')
target_times = pd.DatetimeIndex(np.load('/tmp/target_times.npy').astype('datetime64[ns]'))
hot = np.load('/tmp/hot.npy')
mhw = np.load('/tmp/mhw.npy')

# Check a specific sea cell
sea_indices = np.argwhere(sea_mask)
print("Total sea cells:", len(sea_indices))

# Let's look at a few cells
for lat_i, lon_i in sea_indices[:5]:
    hot_series = hot[:, lat_i, lon_i]
    mhw_series = mhw[:, lat_i, lon_i]
    print(f"\nCell ({lat_i}, {lon_i}): hot days = {hot_series.sum()}, MHW days = {mhw_series.sum()}")
    
    # Show hot days
    hot_days = np.where(hot_series)[0]
    if len(hot_days) > 0:
        print(f"  Hot days at indices: {hot_days}")
        print(f"  Hot dates: {[str(target_times[i].date()) for i in hot_days]}")
    
    mhw_days = np.where(mhw_series)[0]
    if len(mhw_days) > 0:
        print(f"  MHW days at indices: {mhw_days}")
