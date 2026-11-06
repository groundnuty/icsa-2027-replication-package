import numpy as np
from datetime import datetime, timedelta

# Load in_mhw: (n_sea, n_target)
in_mhw = np.load('/tmp/in_mhw.npy')
n_sea, n_target = in_mhw.shape

# Active days: at least one sea cell in MHW
active = in_mhw.any(axis=0)
print(f"Active days: {active.sum()}/{n_target}")

# Target dates
target_dates = []
d = datetime(2019, 6, 1)
while d <= datetime(2019, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

# Find maximal runs of consecutive active days
events = []
i = 0
while i < n_target:
    if active[i]:
        start = i
        while i < n_target and active[i]:
            i += 1
        end = i - 1
        events.append((start, end))
    else:
        i += 1

print(f"Number of regional events: {len(events)}")
for (s, e) in events:
    onset = target_dates[s].strftime('%Y-%m-%d')
    end_date = target_dates[e].strftime('%Y-%m-%d')
    duration = e - s + 1
    print(f"  Event: {onset} to {end_date} (duration: {duration} days)")
