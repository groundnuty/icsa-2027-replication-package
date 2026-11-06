import numpy as np, json
from datetime import date, timedelta

st3 = np.load('/tmp/stage3b.npz')
MHW, hot, sea = st3['A'], st3['hot'], st3['sea']
nt = MHW.shape[0]
target_dates = []
d = date(2013,6,1)
while d <= date(2013,8,31):
    target_dates.append(d); d += timedelta(days=1)
assert len(target_dates) == nt

active = MHW.any(axis=(1,2))    # a day is active if >=1 sea cell inside per-cell MHW
print("active days:", int(active.sum()), "of", nt)
# regional events: maximal runs of consecutive active days
events = []
i = 0
while i < nt:
    if active[i]:
        j = i
        while j+1 < nt and active[j+1]: j += 1
        events.append((i, j)); i = j+1
    else:
        i += 1
print("events:", len(events))
for a,b in events:
    cells_in = MHW[a:b+1].any(axis=0).sum()
    print(f"  {target_dates[a]} .. {target_dates[b]}  (len {b-a+1} d, cells involved {int(cells_in)})")

# per-cell MHW stats
ncell_mhw = MHW.sum(axis=(1,2))
print("per-cell MHW cell-days by day:", [int(x) for x in ncell_mhw])
print("cells with any MHW:", int(MHW.any(axis=0).sum()), "of sea cells", int(sea.sum()))

json.dump({"events":[[a,b] for a,b in events]}, open('/tmp/events.json','w'))
