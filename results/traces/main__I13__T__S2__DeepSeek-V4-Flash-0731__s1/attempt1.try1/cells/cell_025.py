
import numpy as np

sst_target = np.load('sst_target.npy')
sea_cells = np.all(np.isfinite(sst_target), axis=0)
print("Number of sea cells:", sea_cells.sum())
print("Number of non-sea cells:", (~sea_cells).sum())

# Find locations of non-sea cells
non_sea = ~sea_cells
idx = np.argwhere(non_sea)
print("First 10 non-sea cells (lat, lon):")
for i in range(min(10, len(idx))):
    print(f"  ({idx[i][0]}, {idx[i][1]})")
print("Last few:")
for i in range(max(0, len(idx)-5), len(idx)):
    print(f"  ({idx[i][0]}, {idx[i][1]})")

# Print the grid more compactly (show rows where there are land cells)
for lat_i in range(60):
    row = sea_cells[lat_i]
    if not np.all(row):
        print(f"Row {lat_i}: {row.astype(int)}")
