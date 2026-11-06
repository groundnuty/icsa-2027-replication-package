import numpy as np

# Load data
target_data = np.load('/work/target_data.npy').astype(np.float64)
threshold_smooth = np.load('/work/threshold_smooth.npy')

from datetime import datetime, timedelta

def day_of_year(month, day):
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:month-1]) + day

target_dates = []
d = datetime(2007, 6, 1)
while d <= datetime(2007, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

target_doy = np.array([day_of_year(dt.month, dt.day) for dt in target_dates])

# Compute hot mask
sea_mask = np.all(~np.isnan(target_data), axis=0)
hot = np.zeros((92, 60, 60), dtype=bool)
for t in range(92):
    doy = target_doy[t]
    hot[t] = (target_data[t] >= threshold_smooth[:, :, doy-1]) & sea_mask

print(f"Hot mask shape: {hot.shape}")
print(f"Total hot cell-days: {np.sum(hot)}")

# Function to detect per-cell MHWs for a single cell
def detect_cell_mhw(hot_cell):
    """hot_cell: boolean array of length 92.
    Returns: boolean array of length 92, True where inside a per-cell MHW."""
    n = len(hot_cell)
    
    # Find runs of consecutive hot days
    runs = []  # list of (start, end) inclusive
    in_run = False
    for i in range(n):
        if hot_cell[i]:
            if not in_run:
                run_start = i
                in_run = True
        else:
            if in_run:
                runs.append((run_start, i - 1))
                in_run = False
    if in_run:
        runs.append((run_start, n - 1))
    
    # Keep runs of length >= 5
    mhws = [(s, e) for s, e in runs if e - s + 1 >= 5]
    
    # Join MHWs separated by 1-2 non-hot days
    if len(mhws) <= 1:
        joined = mhws
    else:
        joined = [mhws[0]]
        for i in range(1, len(mhws)):
            prev_s, prev_e = joined[-1]
            curr_s, curr_e = mhws[i]
            gap = curr_s - prev_e - 1  # number of non-hot days between
            if gap <= 2:
                # Join
                joined[-1] = (prev_s, curr_e)
            else:
                joined.append((curr_s, curr_e))
    
    # Create mask
    mask = np.zeros(n, dtype=bool)
    for s, e in joined:
        mask[s:e+1] = True
    
    return mask

# Compute per-cell MHW mask for all cells
cell_mhw_mask = np.zeros((92, 60, 60), dtype=bool)
for i in range(60):
    for j in range(60):
        if sea_mask[i, j]:
            cell_mhw_mask[:, i, j] = detect_cell_mhw(hot[:, i, j])

print(f"Per-cell MHW mask shape: {cell_mhw_mask.shape}")
print(f"Total per-cell MHW cell-days: {np.sum(cell_mhw_mask)}")
