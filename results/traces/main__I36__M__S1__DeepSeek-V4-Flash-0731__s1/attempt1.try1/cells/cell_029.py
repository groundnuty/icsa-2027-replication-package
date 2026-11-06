
import numpy as np
from datetime import date

# Load everything
cell_mhw = np.load('/tmp/cell_mhw.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

with open('/tmp/target_dates.txt') as f:
    target_dates_str = [line.strip() for line in f]
target_dates = [date.fromisoformat(s) for s in target_dates_str]

n_days = len(target_dates)

# A day is active if at least one sea cell is in a per-cell MHW
active = cell_mhw.any(axis=(1, 2))
print(f"Active days: {active.sum()} out of {n_days}")

# Show which days are active
for t in range(n_days):
    if active[t]:
        n_cells = cell_mhw[t].sum()
        print(f"  {target_dates[t].isoformat()}: {n_cells} cells in MHW")

# Find maximal runs
events = []
start = None
for t in range(n_days):
    if active[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            events.append((start, t-1))
            start = None
if start is not None:
    events.append((start, n_days-1))

print(f"\nRegional events: {len(events)}")
for s, e in events:
    print(f"  {target_dates[s].isoformat()} to {target_dates[e].isoformat()} ({e-s+1} days)")
