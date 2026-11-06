
import numpy as np
from datetime import date, timedelta
import json

# Load data
mhw_mask = np.load('/tmp/mhw_mask.npy')  # (92, 60, 60)
sea_cells = np.load('/tmp/sea_cells.npy')

n_days, n_lat, n_lon = mhw_mask.shape

# Target dates
target_start = date(2022, 6, 1)
target_end = date(2022, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)

# Determine active days: at least one sea cell in MHW
active = np.any(mhw_mask & sea_cells[np.newaxis, :, :], axis=(1, 2))
print(f"Active days: {active.sum()} out of {n_days}")
for t in range(n_days):
    if active[t]:
        print(f"  Day {target_dates[t]}: active")
    else:
        print(f"  Day {target_dates[t]}: NOT active")

# Find maximal runs of active days
events = []
in_event = False
event_start = 0
for t in range(n_days):
    if active[t]:
        if not in_event:
            event_start = t
            in_event = True
    else:
        if in_event:
            events.append((event_start, t - 1))
            in_event = False
if in_event:
    events.append((event_start, n_days - 1))

print(f"\nRegional events: {len(events)}")
for s, e in events:
    print(f"  {target_dates[s]} to {target_dates[e]} ({e-s+1} days)")
