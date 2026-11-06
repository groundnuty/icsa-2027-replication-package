
import numpy as np
import pandas as pd
import time

def find_per_cell_mhw(hot_array):
    n = len(hot_array)
    in_mhw = np.zeros(n, dtype=bool)
    
    # Find maximal runs of consecutive hot days
    runs = []
    i = 0
    while i < n:
        if hot_array[i]:
            start = i
            while i < n and hot_array[i]:
                i += 1
            end = i - 1
            runs.append((start, end))
        else:
            i += 1
    
    # Keep runs of length >= 5
    mhw_runs = [(s, e) for (s, e) in runs if (e - s + 1) >= 5]
    
    # Join runs separated by 1 or 2 non-hot days
    if not mhw_runs:
        return in_mhw
    
    joined = [mhw_runs[0]]
    for run in mhw_runs[1:]:
        prev_s, prev_e = joined[-1]
        s, e = run
        gap = s - prev_e - 1
        if 1 <= gap <= 2:
            joined[-1] = (prev_s, e)
        else:
            joined.append(run)
    
    for s, e in joined:
        in_mhw[s:e+1] = True
    
    return in_mhw

# Load data
target_sst = np.load('/work/target_sst.npy')
target_time = np.load('/work/target_time.npy', allow_pickle=True)
threshold_smooth = np.load('/work/threshold_smooth.npy')

tt = pd.to_datetime(target_time)
n_target, n_lat, n_lon = target_sst.shape

# Define doy mapping
cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def doy_from_md(m, d):
    return cum[m-1] + d

target_doy = np.array([doy_from_md(t.month, t.day) for t in tt])

# Hot array
hot = np.zeros((n_target, n_lat, n_lon), dtype=bool)
for i in range(n_target):
    d_idx = target_doy[i] - 1
    hot[i] = target_sst[i] >= threshold_smooth[d_idx]

# Sea cells
sea_cells = np.all(np.isfinite(target_sst), axis=0)

# Compute per-cell MHW mask
print("Computing per-cell MHWs...")
start = time.time()

mhw_mask = np.zeros((n_target, n_lat, n_lon), dtype=np.uint8)

for lat in range(n_lat):
    for lon in range(n_lon):
        if sea_cells[lat, lon]:
            hot_cell = hot[:, lat, lon]
            in_mhw = find_per_cell_mhw(hot_cell)
            mhw_mask[:, lat, lon] = in_mhw.astype(np.uint8)

print(f"Per-cell MHW computation took {time.time()-start:.2f}s")

# Verify: land cells are 0
land_cells = ~sea_cells
print("Land cell MHW mask sum:", mhw_mask[:, land_cells].sum())
print("Sea cell MHW mask sum:", mhw_mask[:, sea_cells].sum())

# Count cells with at least one MHW day
print("Cells with at least one MHW day:", (mhw_mask.sum(axis=0) > 0).sum())

# Save the per-cell MHW mask
np.save('/work/mhw_mask.npy', mhw_mask)
print("Saved MHW mask")
