
import numpy as np

mhw_orig = np.load('/tmp/mhw_cell.npy')
mhw_corr = np.load('/tmp/mhw_cell_corrected.npy')

print("Same:", np.array_equal(mhw_orig, mhw_corr))
print("Diff count:", (mhw_orig != mhw_corr).sum())
