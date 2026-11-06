
import numpy as np, datetime as dt, json, os

hot = np.load('/tmp/mhw/hot.npy')
maskA = np.load('/tmp/mhw/maskA.npy')
sea2 = np.load('/tmp/mhw/sea2.npy')
A = np.load('/tmp/mhw/target.npy').squeeze(axis=1)
lat = np.load('/tmp/mhw/lat.npy'); lon = np.load('/tmp/mhw/lon.npy')
NT, NY, NX = 92, 60, 60
tdates = [dt.date(2008,6,1) + dt.timedelta(days=i) for i in range(NT)]

active = maskA.any(axis=1)
events = []
i = 0
while i < NT:
    if active[i]:
        j = i
        while j+1 < NT and active[j+1]:
            j += 1
        events.append((tdates[i], tdates[j]))
        i = j+1
    else:
        i += 1
print("regional events:")
for e in events:
    print(" ", e[0], "->", e[1], f"({(e[1]-e[0]).days+1} days)")

# sanity: number of cells in MHW on event days vs total
m3 = maskA.reshape(NT, NY, NX).astype(np.uint8)
print("mask dtype/shape:", m3.dtype, m3.shape, "sum:", int(m3.sum()))
print("active day counts per event:", [int(active[s:s+1].sum()) for s in [e[0].toordinal()-tdates[0].toordinal() for e in events]])
