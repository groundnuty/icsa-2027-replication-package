
import numpy as np
import pandas as pd
import time

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

# Count per-cell MHWs
print("Cells with at least one MHW day:", (mhw_mask.sum(axis=0) > 0).sum())

# Save the per-cell MHW mask
np.save('/work/mhw_mask.npy', mhw_mask)
print("Saved MHW mask")
