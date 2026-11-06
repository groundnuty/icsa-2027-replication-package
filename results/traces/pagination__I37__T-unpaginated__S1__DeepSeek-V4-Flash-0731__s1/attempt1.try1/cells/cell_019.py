
import numpy as np
import pickle

threshold = np.load('work/threshold.npy')
climatology = np.load('work/climatology.npy')

# For each cell, count NaN across doys
nan_count = np.sum(np.isnan(threshold), axis=0)
print("Cells with NaN count per cell:")
print(f"  0 NaN: {(nan_count == 0).sum()} cells")
print(f"  366 NaN: {(nan_count == 366).sum()} cells")
print(f"  Between 1 and 365: {((nan_count > 0) & (nan_count < 366)).sum()} cells")

# Check which cells have partial NaN
partial = np.where((nan_count > 0) & (nan_count < 366))[0]
print(f"\nPartial NaN cells: {len(partial)}")
if len(partial) > 0:
    print("First few partial NaN cells and their NaN patterns:")
    for c in partial[:5]:
        nan_doy = np.where(np.isnan(threshold[:, c]))[0] + 1
        print(f"  Cell {c}: NaN on doys {nan_doy[:20]}... (count={len(nan_doy)})")
