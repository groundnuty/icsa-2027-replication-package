
import numpy as np
from datetime import date, timedelta

per_cell_mhw = np.load('/tmp/per_cell_mhw.npy')
n_target, n_lat, n_lon = per_cell_mhw.shape

# Target dates
target_dates = []
d = date(2009, 6, 1)
while d <= date(2009, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

# Step 4: Regional events
# A day is active if at least one sea cell is inside a per-cell MHW on that day
active = per_cell_mhw.any(axis=(1, 2))  # shape (n_target,)

print("Active days:", active.sum())

# Regional MHW event is a maximal run of consecutive active days
events = []
t = 0
while t < n_target:
    if active[t]:
        start = t
        while t < n_target and active[t]:
            t += 1
        events.append((start, t-1))
    else:
        t += 1

print(f"Number of regional events: {len(events)}")
for start, end in events:
    print(f"  Event: {target_dates[start]} to {target_dates[end]} ({end-start+1} days)")
