import numpy as np, datetime

target = np.load("/tmp/mhw/target.npy")            # (92, 60, 60)
sea = np.load("/tmp/mhw/sea_cells.npy")            # (60, 60)
sea_idx = np.argwhere(sea)
thr_s = np.load("/tmp/mhw/thr_smooth.npy")         # (nsea, 366)

d0 = datetime.date(2007, 6, 1)
ndays = target.shape[0]
doy_map = {1:(1,31),2:(32,59),3:(61,91),4:(92,121),5:(122,152),6:(153,182),7:(183,213),8:(214,244),9:(245,274),10:(275,305),11:(306,335),12:(336,366)}
def doy(d):
    return doy_map[d.month][0] + d.day - 1 + (1 if d.month == 2 and d.day == 29 else 0)
# simpler: cum table
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy(d):
    return cum[d.month-1] + d.day
assert doy(datetime.date(2007,6,1)) == 153 and doy(datetime.date(2007,8,31)) == 244

doys = np.array([doy(d0 + datetime.timedelta(days=i)) for i in range(ndays)])
print("target doys:", doys[0], "->", doys[-1])

sst_sea = target[:, sea_idx[:,0], sea_idx[:,1]]   # (92, nsea)
# hot: (nsea, 92)
hot = sst_sea.T >= thr_s[:, doys]                 # broadcast (nsea,92)
print("hot fraction:", hot.mean())

# per-cell MHW: runs >=5 hot days, join gaps of 1-2 non-hot days
mask = np.zeros((len(sea_idx), ndays), dtype=np.uint8)
for c in range(len(sea_idx)):
    h = hot[c]
    # find maximal runs of True
    diff = np.diff(h.astype(np.int8))
    starts = list(np.where(diff == 1)[0] + 1)
    if h[0]: starts.insert(0, 0)
    ends = list(np.where(diff == -1)[0])
    if h[-1]: ends.append(ndays - 1)
    runs = [(s, e) for s, e in zip(starts, ends) if e - s + 1 >= 5]
    # join runs separated by <=2 non-hot days
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    for s, e in merged:
        mask[c, s:e+1] = 1

full_mask = np.zeros((ndays, 60, 60), dtype=np.uint8)
full_mask[:, sea_idx[:,0], sea_idx[:,1]] = mask
print("mhw cell-days:", int(full_mask.sum()), "of", full_mask.size)

active = mask.any(axis=0)
# regional events: maximal runs of consecutive active days
events = []
i = 0
while i < ndays:
    if active[i]:
        j = i
        while j + 1 < ndays and active[j+1]:
            j += 1
        onset = d0 + datetime.timedelta(days=i)
        end = d0 + datetime.timedelta(days=j)
        events.append((str(onset), str(end), j - i + 1))
        i = j + 1
    else:
        i += 1
print("regional events:")
for ev in events:
    print("  ", ev[0], "->", ev[1], "len", ev[2])

# activity profile around edges
print("active first 10:", active[:10].astype(int))
print("active last 10:", active[-10:].astype(int))

np.save("/tmp/mhw/full_mask.npy", full_mask)
np.save("/tmp/mhw/events.npy", np.array(events, dtype=object), allow_pickle=True)
print("saved mask & events")
