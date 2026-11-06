import numpy as np, json
from datetime import date, timedelta

mask = np.load('/work/mhw_mask.npy')
meta = json.load(open('/work/meta.json'))
t0 = date.fromisoformat(meta['t0']); t1 = date.fromisoformat(meta['t1'])
nt = (t1-t0).days+1
tdates = [t0+timedelta(days=i) for i in range(nt)]

active = mask.any(axis=(1,2))       # at least one sea cell in a per-cell MHW
print("active days:", int(active.sum()), "of", nt)

# maximal runs of consecutive active days
idx = np.flatnonzero(active)
events = []
if idx.size:
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.concatenate(([idx[0]], idx[breaks+1]))
    ends = np.concatenate((idx[breaks], [idx[-1]]))
    events = [(int(s), int(e)) for s, e in zip(starts, ends)]
print("num regional events:", len(events))
for s,e in events:
    print("event:", tdates[s].isoformat(), "->", tdates[e].isoformat(), f"({e-s+1} days)")
json.dump([[s,e] for s,e in events], open('/work/events.json','w'))

# gap structure between events
for k in range(len(events)-1):
    gap = events[k+1][0] - events[k][1] - 1
    print(f"gap between event {k+1} and {k+2}: {gap} days")
