
import numpy as np
import datetime as dt

mhw_mask = np.load('/tmp/mhw_mask.npy')
tgt_times = np.load('/tmp/tgt_times.npy')

n_time = mhw_mask.shape[0]

# Active days: at least one cell in an MHW on that day
active = np.zeros(n_time, dtype=bool)
for t in range(n_time):
    active[t] = np.any(mhw_mask[t, :, :] > 0)

print("Active days:", active.sum(), "out of", n_time)
for t in range(n_time):
    if active[t]:
        print(f"  Day {t}: {tgt_times[t]} - {mhw_mask[t].sum()} cells in MHW")
    elif t > 0 and active[t-1]:
        print(f"  Day {t}: {tgt_times[t]} - INACTIVE (0 cells)")

# Find maximal runs of consecutive active days
events = []
in_event = False
for t in range(n_time):
    if active[t]:
        if not in_event:
            event_start = t
            in_event = True
    else:
        if in_event:
            events.append((event_start, t-1))
            in_event = False
if in_event:
    events.append((event_start, n_time-1))

print(f"\nRegional events: {len(events)}")
for (start, end) in events:
    start_str = str(tgt_times[start])[:10]
    end_str = str(tgt_times[end])[:10]
    duration = end - start + 1
    print(f"  Event: {start_str} to {end_str} ({duration} days)")
