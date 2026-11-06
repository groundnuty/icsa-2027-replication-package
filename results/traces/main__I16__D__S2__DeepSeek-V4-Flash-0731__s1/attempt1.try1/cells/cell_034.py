
import numpy as np

mhw_mask = np.load('/work/mhw_mask.npy')
hot = None  # need to recompute

# Let me check if any cell has a joined MHW (where the mhw_mask includes gap days)
# For each cell, check if there's a pattern like ...1 0 1... or ...1 0 0 1... within an MHW
n_t, n_lat, n_lon = mhw_mask.shape

joined_cells = []
for ilat in range(n_lat):
    for ilon in range(n_lon):
        m = mhw_mask[:, ilat, ilon]
        # Check for pattern 1 0 1 or 1 0 0 1 (gap inside MHW)
        for i in range(n_t - 2):
            if m[i] == 1 and m[i+1] == 0 and m[i+2] == 1:
                joined_cells.append((ilat, ilon, i))
                break
            if i < n_t - 3 and m[i] == 1 and m[i+1] == 0 and m[i+2] == 0 and m[i+3] == 1:
                joined_cells.append((ilat, ilon, i))
                break

print("Cells with joined MHWs:", len(joined_cells))
if joined_cells:
    print("First few:", joined_cells[:5])
