
import numpy as np
import datetime

mhw_mask = np.load('mhw_mask_per_cell.npy')
target_dates_str = np.load('target_dates.npy', allow_pickle=True)
target_dt = [datetime.datetime.strptime(str(s), '%Y-%m-%d') for s in target_dates_str]

active = mhw_mask.sum(axis=(1, 2)) > 0

# Check boundaries
print("Around event boundaries:")
for t in range(92):
    date_str = target_dt[t].strftime('%Y-%m-%d')
    active_flag = "ACTIVE" if active[t] else "       "
    n_cells = mhw_mask[t].sum()
    print(f"  Day {t} ({date_str}): {active_flag} ({n_cells} cells)")
    if t in [18, 19, 20, 21, 33, 34, 35, 41, 42, 43, 44, 45, 70, 71, 72, 73]:
        pass  # just showing all for clarity
