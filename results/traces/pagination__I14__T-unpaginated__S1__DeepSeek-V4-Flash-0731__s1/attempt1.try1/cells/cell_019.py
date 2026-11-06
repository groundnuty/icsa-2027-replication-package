
import numpy as np
from datetime import date, timedelta

# Load per-cell MHW data
per_cell_mhw = np.load('per_cell_mhw.npy')  # (92, 60, 60)
sea_mask = np.load('sea_mask.npy')

# A day is active if at least one sea cell is in a per-cell MHW
active = np.any(per_cell_mhw, axis=(1, 2))  # (92,) boolean

print(f"Active days: {active.sum()}")
print(f"Active day indices: {np.where(active)[0]}")

# Target dates
target_dates = []
d = date(2015, 6, 1)
while d <= date(2015, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

# Find maximal runs of consecutive active days
events = []
i = 0
while i < len(active):
    if active[i]:
        start = i
        while i < len(active) and active[i]:
            i += 1
        events.append((start, i-1))
    else:
        i += 1

print(f"\nNumber of regional events: {len(events)}")
for s, e in events:
    print(f"  Event: {target_dates[s].isoformat()} to {target_dates[e].isoformat()} ({e-s+1} days)")
