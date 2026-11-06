
import numpy as np

mhw_mask = np.load('/work/mhw_mask.npy')

# For each of the first 10 days, count cells in MHW
for i in range(10):
    count = np.sum(mhw_mask[i, :, :])
    print(f"Day {i}: {count} cells in MHW")
