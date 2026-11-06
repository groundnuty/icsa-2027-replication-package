
import numpy as np

mhw_mask = np.load('/work/mhw_mask.npy')

# Check days 10-20
for i in range(10, 20):
    count = np.sum(mhw_mask[i, :, :])
    print(f"Day {i}: {count} cells in MHW")
