
import numpy as np
import pandas as pd

# Load data
mhw = np.load('/tmp/mhw.npy')
target_times = pd.DatetimeIndex(np.load('/tmp/target_times.npy').astype('datetime64[ns]'))

# Check active days
active = np.any(mhw, axis=(1, 2))
print("Active days:", np.where(active)[0])
print("Active dates:", [str(target_times[i].date()) for i in np.where(active)[0]])

# Find events
events = []
in_event = False
start = 0
for i in range(len(active)):
    if active[i] and not in_event:
        start = i
        in_event = True
    elif not active[i] and in_event:
        events.append((start, i - 1))
        in_event = False
if in_event:
    events.append((start, len(active) - 1))

print("\nRegional events:")
for s, e in events:
    print(f"  {target_times[s].date()} to {target_times[e].date()}, duration={e-s+1} days")

# Verify no active day is missed
active_days_set = set(np.where(active)[0])
event_days_set = set()
for s, e in events:
    event_days_set.update(range(s, e + 1))
print(f"\nActive days in events: {len(event_days_set)}, expected: {len(active_days_set)}")
if active_days_set != event_days_set:
    print("MISMATCH!")
    print("Active not in events:", active_days_set - event_days_set)
    print("In events not active:", event_days_set - active_days_set)
else:
    print("All active days are in events")
