
import numpy as np

old_mask = np.load('/tmp/mhw_mask.npy')
new_mask = np.load('/tmp/mhw_mask_corrected.npy')

old_active = old_mask.sum(axis=(1,2)) > 0
new_active = new_mask.sum(axis=(1,2)) > 0

print("Old active days:", np.where(old_active)[0])
print("New active days:", np.where(new_active)[0])
print("Same active days:", np.array_equal(old_active, new_active))

# Check if any day is active in old but not new, or vice versa
diff = old_active != new_active
print(f"Different: {np.where(diff)[0]}")
