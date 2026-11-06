
import numpy as np
import pickle
import datetime

# Load data
mhw_mask = np.load('/tmp/mhw_mask.npy')
hot = np.load('/tmp/hot.npy')
target_sst = np.load('/tmp/target_sst.npy').astype(np.float64)
sea_cells = np.load('/tmp/sea_cells.npy')

# Verify active days
active = mhw_mask.max(axis=(1, 2)) > 0
print(f"Active pattern (first 10): {active[:10]}")
print(f"Active pattern (days 60-75): {active[60:75]}")
print(f"Active pattern (last 10): {active[-10:]}")
print(f"Total active days: {active.sum()}")

# Verify regional events
events = []
i = 0
while i < len(active):
    if active[i]:
        j = i
        while j < len(active) and active[j]:
            j += 1
        events.append((i, j-1))
        i = j
    else:
        i += 1

print(f"Regional events: {len(events)}")
for s, e in events:
    sd = datetime.date(2021, 6, 1) + datetime.timedelta(days=s)
    ed = datetime.date(2021, 6, 1) + datetime.timedelta(days=e)
    print(f"  Event {s}-{e}: {sd} to {ed} ({e-s+1} days)")

# Verify: is the active pattern correct?
# Check: on day 68 (Aug 8), is any cell active? On day 69 (Aug 9)?
print(f"\nDay 68 (Aug 8) active: {active[68]}")
print(f"Day 69 (Aug 9) active: {active[69]}")
print(f"Day 67 (Aug 7) active: {active[67]}")

# Check how many cells are in MHWs on day 68
print(f"Cells in MHW on day 68: {mhw_mask[68].sum()}")
print(f"Cells in MHW on day 69: {mhw_mask[69].sum()}")
print(f"Cells in MHW on day 60: {mhw_mask[60].sum()}")

# Check: which cells have MHWs ending on day 68?
end_day_68 = mhw_mask[68].sum(axis=0)  # Not right, let me check differently
# Count cells in MHW on each day
daily_count = mhw_mask.sum(axis=(1, 2))
print(f"\nDaily cell count in MHWs (first 10): {daily_count[:10]}")
print(f"Daily cell count in MHWs (days 55-75): {daily_count[55:75]}")
print(f"Daily cell count in MHWs (last 10): {daily_count[-10:]}")
