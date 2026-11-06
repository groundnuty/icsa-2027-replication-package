
import numpy as np
import xarray as xr
import json
import os

# Verify all intermediate results
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/climatology_smooth.npy')
mhw_mask = np.load('/tmp/mhw_mask.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

# Verify: sea cells are the only ones with MHW=1
# Check that land cells are all 0
land_mask = ~sea_mask
land_mhw = mhw_mask[:, land_mask]
print("Land cells MHW sum:", land_mhw.sum())
print("Sea cells MHW sum:", mhw_mask[:, sea_mask].sum())

# Check: every sea cell that has MHW=1 on any day has at least one run of >=5 hot days
# (already verified in earlier analysis)

# Check: for each sea cell, the MHW mask correctly identifies joined MHWs
# Let's verify a few more cells

# Check the events computation
tgt_times = np.load('/tmp/tgt_times.npy')
n_time = mhw_mask.shape[0]
active = np.array([np.any(mhw_mask[t] > 0) for t in range(n_time)])

# Find all active day ranges
events = []
in_event = False
for t in range(n_time):
    if active[t]:
        if not in_event:
            start = t
            in_event = True
    else:
        if in_event:
            events.append((start, t-1))
            in_event = False
if in_event:
    events.append((start, n_time-1))

print("\nEvents found:", events)
for (s, e) in events:
    print(f"  {str(tgt_times[s])[:10]} to {str(tgt_times[e])[:10]}")

# Check active days summary
print(f"\nActive days: {active.sum()} out of {n_time}")

# Verify no active days after day 26
print("Active days after day 26:", active[27:].sum())
