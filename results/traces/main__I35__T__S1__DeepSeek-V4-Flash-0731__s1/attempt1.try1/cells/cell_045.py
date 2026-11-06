
import numpy as np

# Compare float32 (corrected) and float64 MHW masks
mhw_f32 = np.load('/tmp/mhw_mask_corrected.npy')
mhw_f64 = np.load('/tmp/mhw_mask_f64.npy')

print(f"Float32 MHW sum: {mhw_f32.sum()}")
print(f"Float64 MHW sum: {mhw_f64.sum()}")
print(f"Same: {np.array_equal(mhw_f32, mhw_f64)}")

if not np.array_equal(mhw_f32, mhw_f64):
    diff = mhw_f32 != mhw_f64
    print(f"Differences: {diff.sum()}")
    diff_cells = np.argwhere(diff.any(axis=0))
    print(f"Cells with differences: {len(diff_cells)}")
    for idx in diff_cells[:5]:
        i, j = idx
        print(f"  Cell ({i},{j}): f32 days {np.where(mhw_f32[:,i,j]>0)[0]}, f64 days {np.where(mhw_f64[:,i,j]>0)[0]}")
