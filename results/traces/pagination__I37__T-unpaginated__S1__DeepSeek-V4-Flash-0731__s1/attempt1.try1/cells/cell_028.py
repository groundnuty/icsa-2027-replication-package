
import numpy as np
cell_mhw = np.load('work/cell_mhw.npy')
print(f"Cell MHW shape: {cell_mhw.shape}")
print(f"Sum: {cell_mhw.sum()}")
print(f"Any: {cell_mhw.any()}")
