
import numpy as np
import datetime

# Load MHW mask
mhw_mask = np.load('mhw_mask.npy')

# Active days
active = mhw_mask.sum(axis=(1, 2)) > 0
print("Active days:", np.where(active)[0])

# Find regional events (maximal runs of consecutive active days)
events = []
in_event = False
start = 0
for t in range(len(active)):
    if active[t] and not in_event:
        in_event = True
        start = t
    elif not active[t] and in_event:
        in_event = False
        events.append((start, t-1))
if in_event:
    events.append((start, len(active)-1))

print(f"\nRegional events: {len(events)}")
target_start = datetime.date(2007, 6, 1)
for s, e in events:
    onset = target_start + datetime.timedelta(days=s)
    end = target_start + datetime.timedelta(days=e)
    print(f"  Event: {onset} to {end} (days {s} to {e}, {e-s+1} days)")
