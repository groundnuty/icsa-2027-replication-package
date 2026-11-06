
import numpy as np

mhw_mask = np.load('/tmp/mhw_mask_correct.npy')
active = mhw_mask.sum(axis=(1, 2)) > 0
print("Active days pattern:")
for i in range(len(active)):
    if active[i]:
        print(f"  Day {i}: active ({mhw_mask[i].sum()} cells in MHW)")
    else:
        print(f"  Day {i}: inactive")
