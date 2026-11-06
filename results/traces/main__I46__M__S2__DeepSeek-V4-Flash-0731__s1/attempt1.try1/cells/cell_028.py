
import numpy as np

# Load the mhw mask and check activity pattern
mhw_mask = np.load('/tmp/mhw_mask.npy')
hot = np.load('/tmp/hot.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

# Active days (any sea cell in MHW)
active = mhw_mask.any(axis=(1, 2))

print("Active days (days 0-91):")
for i in range(len(active)):
    if active[i]:
        print(f"  Day {i}: active, {mhw_mask[i].sum()} cell-days in MHW")
    else:
        print(f"  Day {i}: inactive")

print()
print("Number of active days:", active.sum())
print("Number of inactive days:", (~active).sum())
