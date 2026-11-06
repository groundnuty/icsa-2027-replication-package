
import numpy as np

tgt_data = np.load('/work/tgt_data.npy').astype(np.float64)
tgt_nan = np.isnan(tgt_data)

# Per-cell NaN counts
nan_count = tgt_nan.sum(axis=0)  # (60, 60)
partial_nan = (nan_count > 0) & (nan_count < 92)
full_nan = nan_count == 92

print(f"Cells with no NaN: {(nan_count == 0).sum()}")
print(f"Cells with partial NaN (1-91 days): {partial_nan.sum()}")
print(f"Cells with all NaN (92 days): {full_nan.sum()}")

# Check the partial NaN cells
if partial_nan.sum() > 0:
    idx = np.where(partial_nan)
    for k in range(min(5, partial_nan.sum())):
        i, j = idx[0][k], idx[1][k]
        print(f"  Cell ({i},{j}): {nan_count[i,j]} NaN days out of 92")
