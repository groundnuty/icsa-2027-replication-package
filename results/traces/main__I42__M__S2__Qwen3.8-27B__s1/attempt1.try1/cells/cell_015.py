import numpy as np, pickle

target = np.load('/tmp/target.npy')   # (92, 60, 60)
time_all = np.load('/tmp/time_all.npy')
target_dates = time_all[11109:11201]
thr_s = np.load('/tmp/thr_s.npy')     # (366, 3600)

LEAP_CUM = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
def doy366(dates):
    dates = np.asarray(dates).astype('datetime64[D]')
    m = (dates.astype('datetime64[M]') - dates.astype('datetime64[Y]')).astype(int) + 1
    d = (dates - dates.astype('datetime64[M]')).astype(int) + 1
    return LEAP_CUM[m - 1] + d

doy_t = doy366(target_dates)          # (92,)
assert doy_t.tolist() == list(range(153, 245))

S = target.reshape(92, -1)            # (92, 3600)
sea = np.isfinite(S).all(axis=0)
print("sea cells:", int(sea.sum()), "of 3600")

thr_t = thr_s[doy_t - 1]              # (92, 3600)
hot = S >= thr_t
hot = hot & np.isfinite(S)            # non-finite SST can't be hot
hot &= sea[None, :]

# per-cell: runs of >=5 consecutive hot days; merge events separated by 1-2 non-hot days
ND = 92
mask = np.zeros((ND, 3600), dtype=np.uint8)
n_events_cell = np.zeros(3600, dtype=int)
for c in range(3600):
    h = hot[:, c]
    runs = []
    i = 0
    while i < ND:
        if h[i]:
            j = i
            while j + 1 < ND and h[j + 1]:
                j += 1
            if j - i + 1 >= 5:
                runs.append([i, j])
            i = j + 1
        else:
            i += 1
    events = []
    for a, b in runs:
        if events and a - events[-1][1] - 1 <= 2:
            events[-1][1] = b
        else:
            events.append([a, b])
    n_events_cell[c] = len(events)
    for a, b in events:
        mask[a:b + 1, c] = 1

print("cells with >=1 per-cell MHW:", int((n_events_cell > 0).sum()))
print("per-cell event count distribution:", {k: int(((n_events_cell == k).sum())) for k in range(0, n_events_cell.max() + 1)})

mask3d = mask.reshape(92, 60, 60)
active = mask.any(axis=1)
print("active days:", int(active.sum()), "of 92")

# regional events: maximal runs of consecutive active days
reg_events = []
i = 0
while i < ND:
    if active[i]:
        j = i
        while j + 1 < ND and active[j + 1]:
            j += 1
        reg_events.append((i, j))
        i = j + 1
    else:
        i += 1
for a, b in reg_events:
    print("regional event:", target_dates[a], "->", target_dates[b], f"({b-a+1} days)")

np.save('/tmp/mask.npy', mask3d)
with open('/tmp/reg_events.pkl', 'wb') as f:
    pickle.dump([(str(target_dates[a])[:10], str(target_dates[b])[:10]) for a, b in reg_events], f)
print("saved mask and events")
