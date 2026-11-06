
import numpy as np
import pandas as pd

# Load data
mhw_mask = np.load('/work/mhw_mask.npy')  # (92, 60, 60) uint8
target_time = np.load('/work/target_time.npy', allow_pickle=True)
tt = pd.to_datetime(target_time)
target_sst = np.load('/work/target_sst.npy')
threshold_smooth = np.load('/work/threshold_smooth.npy')

# Verify the mhw_mask has correct dimensions and values
print("MHW mask shape:", mhw_mask.shape)
print("MHW mask dtype:", mhw_mask.dtype)
print("MHW mask unique values:", np.unique(mhw_mask))
print("MHW mask sum:", mhw_mask.sum())

# Verify that sea cells have MHW=1 where appropriate, and land cells have MHW=0
sea_cells = np.all(np.isfinite(target_sst), axis=0)
land_cells = ~sea_cells
print(f"\nSea cells: {sea_cells.sum()}, Land cells: {land_cells.sum()}")
print(f"Land cell MHW sum (should be 0): {mhw_mask[:, land_cells].sum()}")

# Find a specific cell that's in an MHW and verify the detection
# Find a sea cell with MHW days
mhw_cell = mhw_mask.sum(axis=0)  # (60,60)
hot_cells = np.where(mhw_cell > 0)
print(f"\nCells with MHW: {len(hot_cells[0])}")

# Pick the first sea cell with MHW
lat_i, lon_i = hot_cells[0][0], hot_cells[1][0]
print(f"Example cell: lat_idx={lat_i}, lon_idx={lon_i}, sea_cell={sea_cells[lat_i, lon_i]}")
print(f"MHW days for this cell: {np.where(mhw_mask[:, lat_i, lon_i] > 0)[0]}")
print(f"MHW day indices: {np.where(mhw_mask[:, lat_i, lon_i] > 0)[0]}")

# Verify the detection manually for this cell
# Check hot/cold for each target day
# Load the threshold and hot array
cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_from_md(m, d):
    return cum[m-1] + d

target_doy = np.array([doy_from_md(t.month, t.day) for t in tt])
hot = np.zeros((92, 60, 60), dtype=bool)
for i in range(92):
    d_idx = target_doy[i] - 1
    hot[i] = target_sst[i] >= threshold_smooth[d_idx]

# Check the cell's hot days
hot_cell = hot[:, lat_i, lon_i]
print(f"\nHot days for this cell: {np.where(hot_cell)[0]}")
print(f"MHW days from mask: {np.where(mhw_mask[:, lat_i, lon_i] > 0)[0]}")

# Verify the per-cell MHW detection
# Find runs of >= 5 hot days
runs = []
i = 0
n = len(hot_cell)
while i < n:
    if hot_cell[i]:
        start = i
        while i < n and hot_cell[i]:
            i += 1
        end = i - 1
        runs.append((start, end))
    else:
        i += 1

print(f"\nRuns of hot days: {runs}")
mhw_runs = [(s, e) for (s, e) in runs if (e - s + 1) >= 5]
print(f"MHW runs (>= 5 days): {mhw_runs}")

# Check SST and threshold for this cell around the MHW period
print("\nSST and threshold for the example cell:")
for i in range(92):
    if mhw_mask[i, lat_i, lon_i] > 0 or hot_cell[i]:
        sst_val = target_sst[i, lat_i, lon_i]
        thresh_val = threshold_smooth[target_doy[i]-1, lat_i, lon_i]
        is_hot = hot_cell[i]
        in_mhw = mhw_mask[i, lat_i, lon_i] > 0
        print(f"  Day {i} ({tt[i].strftime('%Y-%m-%d')}): SST={sst_val:.2f}, Thresh={thresh_val:.2f}, Hot={is_hot}, In_MHW={in_mhw}")
