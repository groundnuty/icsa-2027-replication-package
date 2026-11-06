
import numpy as np
import pandas as pd

# Load
sst_target = np.load('/tmp/sst_target.npy').astype(np.float64)  # (92, 60, 60)
sea_cells = np.load('/tmp/sea_cells.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')  # (367, 60, 60)
target_dates = np.load('/tmp/target_dates.npy')

print("Target SST shape:", sst_target.shape)
print("Target dates:", pd.to_datetime(target_dates[0]), "to", pd.to_datetime(target_dates[-1]))

# Function to compute doy
def doy_from_md(month, day):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month[:month-1]) + day

# Get doy for each target date
target_doy = np.array([doy_from_md(pd.Timestamp(d).month, pd.Timestamp(d).day) for d in target_dates])
print("Target doy:", target_doy)

# For each day and each cell, determine if hot (SST >= threshold)
# sst_target: (92, 60, 60)
# threshold_smooth[target_doy]: (92, 60, 60)
threshold_for_target = threshold_smooth[target_doy]  # (92, 60, 60)
hot = (sst_target >= threshold_for_target) & sea_cells  # (92, 60, 60)

print("Hot day counts:")
for d in range(92):
    n_hot = hot[d].sum()
    if n_hot > 0:
        print(f"  {pd.Timestamp(target_dates[d])}: {n_hot} hot cells")

np.save('/tmp/hot.npy', hot)
np.save('/tmp/target_doy.npy', target_doy)
print("Saved hot array")
