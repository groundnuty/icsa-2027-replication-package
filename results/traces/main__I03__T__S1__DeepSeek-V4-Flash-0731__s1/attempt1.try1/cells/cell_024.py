
import numpy as np
import datetime

# Load
mhw_mask = np.load('mhw_mask_per_cell.npy')  # (92, 60, 60) uint8
target_dates_str = np.load('target_dates.npy', allow_pickle=True)
target_dt = [datetime.datetime.strptime(str(s), '%Y-%m-%d') for s in target_dates_str]

ntarget = mhw_mask.shape[0]

# A day is active if at least one sea cell is inside a per-cell MHW
# But note: land cells are 0, and we only consider sea cells anyway
# mhw_mask already has 1 only for sea cells inside MHWs (land cells are 0)
active = mhw_mask.sum(axis=(1, 2)) > 0  # (92,)

print("Active days:", np.where(active)[0])

# Regional events: maximal runs of consecutive active days
events = []
i = 0
while i < ntarget:
    if active[i]:
        start = i
        while i < ntarget and active[i]:
            i += 1
        end = i - 1
        events.append([start, end])
    else:
        i += 1

print(f"\nNumber of regional events: {len(events)}")
for start, end in events:
    print(f"  {target_dt[start].strftime('%Y-%m-%d')} to {target_dt[end].strftime('%Y-%m-%d')} ({end-start+1} days)")

# Check: are there any cells with MHW on each active day?
print("\nActive days detail:")
for t in range(ntarget):
    if active[t]:
        n_cells = mhw_mask[t].sum()
        print(f"  Day {t} ({target_dt[t].strftime('%Y-%m-%d')}): {n_cells} cells in MHW")
