import numpy as np
import xarray as xr

# Load mhw mask
mhw = np.load('/tmp/mhw_mask.npy')  # (92, 60, 60)

# Find active days
active = np.any(mhw, axis=(1, 2))
print("Active days:", np.where(active)[0])

# Check which cells have MHW on each active day
from collections import Counter

target_ds = xr.open_dataset('/tmp/target_data.nc')
target_time = target_ds['time'].values
import pandas as pd
target_dates = [pd.Timestamp(t).to_pydatetime().date() for t in target_time]

for t in np.where(active)[0]:
    cells = np.argwhere(mhw[t])
    print(f"{target_dates[t]}: {len(cells)} cells in MHW")
