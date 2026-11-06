
import numpy as np
import pandas as pd

# Load data
tgt_data = np.load('/tmp/tgt_data.npy')
tgt_times = np.load('/tmp/tgt_times.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
lats = np.load('/tmp/lats.npy')
lons = np.load('/tmp/lons.npy')

def day_of_year(month, day):
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if month == 2 and day == 29:
        return 60
    doy = sum(days_in_month[:month-1]) + day
    if month > 2:
        doy += 1
    return doy

tgt_doy = np.array([day_of_year(pd.Timestamp(t).to_pydatetime().month, 
                                pd.Timestamp(t).to_pydatetime().day) for t in tgt_times])

# Sea cells
sea_mask = np.all(np.isfinite(tgt_data), axis=0)

# Compute hot days
N_t = len(tgt_times)
hot = np.zeros((N_t, 60, 60), dtype=bool)
for t in range(N_t):
    doy = tgt_doy[t]
    hot[t] = tgt_data[t] >= threshold_smooth[doy-1]
hot = hot & sea_mask

# For each sea cell, find per-cell MHWs
# An MHW is a run of >=5 consecutive hot days, joined if separated by 1-2 non-hot days

# mhw_mask[t, i, j] = True if cell (i,j) is inside a per-cell MHW on day t
mhw_mask = np.zeros((N_t, 60, 60), dtype=bool)

sea_idx = np.where(sea_mask)
for k in range(len(sea_idx[0])):
    i, j = sea_idx[0][k], sea_idx[1][k]
    
    # Get hot days for this cell
    cell_hot = hot[:, i, j]  # shape (N_t,)
    
    # Find runs of hot days
    # First, expand: a hot day is part of a run, and a non-hot day between runs can be joined
    # if the gap is 1 or 2 days
    
    # Step 1: Find initial runs of consecutive hot days (length >= 1)
    # Step 2: Join runs separated by 1-2 non-hot days
    # Step 3: Only keep joined runs with length >= 5
    
    # First find all hot runs
    runs = []  # list of (start, end) inclusive
    t = 0
    while t < N_t:
        if cell_hot[t]:
            start = t
            while t < N_t and cell_hot[t]:
                t += 1
            end = t - 1
            runs.append((start, end))
        else:
            t += 1
    
    if not runs:
        continue
    
    # Join runs separated by 1-2 non-hot days
    joined = [runs[0]]
    for r in runs[1:]:
        prev_end = joined[-1][1]
        gap = r[0] - prev_end - 1
        if gap >= 1 and gap <= 2:
            # Join
            joined[-1] = (joined[-1][0], r[1])
        else:
            joined.append(r)
    
    # Only keep runs of length >= 5
    for start, end in joined:
        length = end - start + 1
        if length >= 5:
            mhw_mask[start:end+1, i, j] = True

print("Cells with at least one MHW day:", (mhw_mask.sum(axis=0) > 0).sum())
print("Total MHW day-cell counts:", mhw_mask.sum())

# Check daily MHW activity
daily_mhw = mhw_mask.sum(axis=(1,2))
print("Daily MHW cell counts:", daily_mhw)

# Regional events: day active if at least one sea cell is in a per-cell MHW
active = daily_mhw > 0
print("Active days:", np.where(active)[0])
print("Active dates:", [str(pd.Timestamp(tgt_times[t]).date()) for t in np.where(active)[0]])
