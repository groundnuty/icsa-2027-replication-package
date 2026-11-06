import numpy as np, json
from datetime import date, timedelta

st3 = np.load('/tmp/stage3b.npz')
MHW2, hot, sea = st3['A'], st3['hot'], st3['sea']
nt, NC = MHW2.shape
MHW = MHW2.reshape(nt, 60, 60)

target_dates = []
d = date(2013,6,1)
while d <= date(2013,8,31):
    target_dates.append(d); d += timedelta(days=1)
assert len(target_dates) == nt

active = MHW.any(axis=(1,2))
print("active days:", int(active.sum()), "of", nt)
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

print("per-cell MHW cell-days by day:", [int(x) for x in MHW.sum(axis=(1,2))])
print("cells with any MHW:", int(MHW.any(axis=0).sum()), "of sea cells", int(sea.sum()))
np.save('/tmp/mhw_final.npy', MHW.astype(np.uint8))
