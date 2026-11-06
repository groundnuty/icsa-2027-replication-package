
import numpy as np

mhw_mask = np.load('/tmp/mhw_mask_correct.npy')
li, lo = 0, 5
cell_mhw = mhw_mask[:, li, lo]
print("Cell MHW mask:", cell_mhw.astype(int))
print("Sum:", cell_mhw.sum())
