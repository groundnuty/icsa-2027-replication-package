
import numpy as np
from datetime import date, timedelta

per_cell_mhw = np.load('/tmp/per_cell_mhw.npy')

# Target dates
target_dates = []
d = date(2009, 6, 1)
while d <= date(2009, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

# Regional events
active = per_cell_mhw.any(axis=(1, 2))
print("Active days:", active.sum())

events = []
t = 0
while t < len(active):
    if active[t]:
        start = t
        while t < len(active) and active[t]:
            t += 1
        events.append((start, t-1))
    else:
        t += 1

for start, end in events:
    print(f"  Event: {target_dates[start].strftime('%Y-%m-%d')} to {target_dates[end].strftime('%Y-%m-%d')} ({end-start+1} days)")
