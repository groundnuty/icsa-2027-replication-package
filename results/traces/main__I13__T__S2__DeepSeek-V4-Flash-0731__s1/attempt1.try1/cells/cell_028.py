
import numpy as np
import datetime

# Load data
sst_target = np.load('sst_target.npy')
hot = np.load('hot.npy')
lat_vals = np.load('lat_vals.npy')
lon_vals = np.load('lon_vals.npy')
target_times_int = np.load('target_times.npy')
target_times = target_times_int.astype('datetime64[D]')

print("Hot shape:", hot.shape)
print("Target times:", target_times[0], "to", target_times[-1])

# Sea cells
sea_cells = np.all(np.isfinite(sst_target), axis=0)
print("Sea cells:", sea_cells.sum())

# Find per-cell MHWs for each sea cell
def find_mhws(hot):
    """Find per-cell MHWs from a boolean array of hot days.
    Returns list of (start_idx, end_idx) inclusive.
    """
    n = len(hot)
    runs = []
    i = 0
    while i < n:
        if hot[i]:
            j = i
            while j < n and hot[j]:
                j += 1
            runs.append((i, j-1))
            i = j
        else:
            i += 1
    
    mhws = [(s, e) for s, e in runs if e - s + 1 >= 5]
    
    if len(mhws) <= 1:
        return mhws
    
    joined = [mhws[0]]
    for s, e in mhws[1:]:
        prev_s, prev_e = joined[-1]
        gap = s - prev_e - 1
        if gap <= 2:
            joined[-1] = (prev_s, e)
        else:
            joined.append((s, e))
    
    return joined

# Create mhw_mask (time, lat, lon) as uint8
mhw_mask = np.zeros((len(target_times), len(lat_vals), len(lon_vals)), dtype=np.uint8)

# Per-cell MHWs for each sea cell
cell_mhws = {}  # (lat_idx, lon_idx) -> list of (start_idx, end_idx)

for lat_i in range(60):
    for lon_i in range(60):
        if sea_cells[lat_i, lon_i]:
            hot_cell = hot[:, lat_i, lon_i]
            mhws = find_mhws(hot_cell)
            cell_mhws[(lat_i, lon_i)] = mhws
            for s, e in mhws:
                mhw_mask[s:e+1, lat_i, lon_i] = 1

print("Number of cells with at least one MHW:", sum(1 for m in cell_mhws.values() if len(m) > 0))
print("Number of MHWs across all cells:", sum(len(m) for m in cell_mhws.values()))
print("MHW mask shape:", mhw_mask.shape)
print("MHW mask sum:", mhw_mask.sum())

# Show some sample per-cell MHWs
for (lat_i, lon_i), mhws in list(cell_mhws.items())[:5]:
    if mhws:
        print(f"Cell ({lat_i},{lon_i}): MHWs at target day indices {mhws}")

np.save('mhw_mask.npy', mhw_mask)
np.save('cell_mhws.npy', np.array([(k[0], k[1], v) for k, v in cell_mhws.items() if len(v) > 0], dtype=object), allow_pickle=True)
