
import numpy as np
import datetime

# Load MHW mask
mhw_mask = np.load('mhw_mask.npy')  # shape (92, 60, 60)

# A day is active if at least one cell is in a per-cell MHW
active = mhw_mask.sum(axis=(1, 2)) > 0
print(f"Active days: {np.sum(active)} out of {len(active)}")

# Print which days are active
target_start = datetime.date(2007, 6, 1)
for t in range(len(active)):
    if active[t]:
        date = target_start + datetime.timedelta(days=t)
        print(f"  Day {t} ({date}): active")
