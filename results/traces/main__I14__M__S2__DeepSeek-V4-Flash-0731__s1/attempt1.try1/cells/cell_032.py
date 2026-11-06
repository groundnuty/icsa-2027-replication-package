
import numpy as np
import pandas as pd
import json

# Independent verification of events
mhw_mask = np.load('/tmp/mhw_mask.npy')
times_int = np.load('/tmp/times.npy')
times = pd.to_datetime(times_int, unit='D')
target_indices = np.load('/tmp/target_indices.npy')

# Active days
active = (mhw_mask.sum(axis=0) > 0)
active_indices = np.where(active)[0]
print("Active day indices:", active_indices)
print("Active dates:", [times[target_indices[i]].date() for i in active_indices])

# Maximal runs
events = []
i = 0
while i < len(active):
    if active[i]:
        j = i
        while j < len(active) and active[j]:
            j += 1
        events.append({
            "onset": str(times[target_indices[i]].date()),
            "end": str(times[target_indices[j-1]].date())
        })
        i = j
    else:
        i += 1

print("\nRegional events:", events)

# Verify against report
with open('output/report.json') as f:
    report = json.load(f)
print("\nReport events:", report['events'])
print("Match:", events == report['events'])
