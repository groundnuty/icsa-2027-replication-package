
import numpy as np
from datetime import datetime

mhw_mask = np.load('output/mhw_mask.npy')
target_dates = np.load('output/target_dates.npy')

# Regional activity: at least one sea cell in an MHW on that day
active = mhw_mask.sum(axis=(1, 2)) > 0

print(f"Active days: {active.sum()} / {len(active)}")

# Find maximal runs of consecutive active days
events = []
i = 0
while i < len(active):
    if active[i]:
        start = i
        while i < len(active) and active[i]:
            i += 1
        end = i - 1
        events.append((start, end))
    else:
        i += 1

print(f"Regional events: {len(events)}")

for start, end in events:
    onset_idx = start
    end_idx = end
    onset_date = datetime.utcfromtimestamp(target_dates[onset_idx].astype('datetime64[ns]').astype(np.int64) / 1e9)
    end_date = datetime.utcfromtimestamp(target_dates[end_idx].astype('datetime64[ns]').astype(np.int64) / 1e9)
    print(f"  Event: {onset_date.date()} to {end_date.date()} ({end - start + 1} days)")
