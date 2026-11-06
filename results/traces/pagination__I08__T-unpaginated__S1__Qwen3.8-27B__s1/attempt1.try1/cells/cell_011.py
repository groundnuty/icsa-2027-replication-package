import numpy as np, datetime, json, time
import fsspec, xarray as xr

t0 = time.time()
Xt = np.load('work/part_t1.npy')            # (92,60,60)
thr_s = np.load('work/thr_s.npy')           # (366, 3600)
sea = np.load('work/sea.npy')               # (60,60)
tday_doy = np.load('work/tday_doy.npy')     # (92,)

T = Xt.shape[0]
ncell = 60*60

# hot days: SST (kelvin, as stored, float64) >= cell threshold for that DOY
thrt = thr_s[tday_doy - 1].reshape(T, 60, 60)      # (92,60,60)
hot = Xt >= thrt
hot &= np.isfinite(Xt)   # NaN days are not hot (all sea cells finite anyway)
print("hot fraction:", hot.mean())

# per-cell MHWs: runs of >=5 hot days, join runs separated by 1-2 non-hot days (gap days included)
mask = np.zeros((T, 60, 60), dtype=np.uint8)
sea_idx = np.argwhere(sea)
n_events_per_cell = 0
cells_with_mhw = 0
def mhw_runs(h):
    """h: bool array length T -> list of (start,end) inclusive MHW spans after merging."""
    T = len(h)
    runs = []
    i = 0
    while i < T:
        if h[i]:
            j = i
            while j + 1 < T and h[j+1]:
                j += 1
            if j - i + 1 >= 5:
                runs.append([i, j])
            i = j + 1
        else:
            i += 1
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] - 1 <= 2:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return merged

for (ci, cj) in sea_idx:
    runs = mhw_runs(hot[:, ci, cj])
    if runs:
        cells_with_mhw += 1
        n_events_per_cell += len(runs)
        for (a, b) in runs:
            mask[a:b+1, ci, cj] = 1
print("cells with >=1 MHW:", cells_with_mhw, "| per-cell MHW count:", n_events_per_cell, time.time()-t0)

# regional events: active = any sea cell inside a per-cell MHW
active = (mask.sum(axis=(1,2)) > 0)
print("active days:", int(active.sum()), "of", T)
events = []
i = 0
while i < T:
    if active[i]:
        j = i
        while j + 1 < T and active[j+1]:
            j += 1
        events.append((i, j))
        i = j + 1
    else:
        i += 1
tdates = [datetime.date(2007,6,1) + datetime.timedelta(days=k) for k in range(T)]
ev_list = [{"onset": tdates[a].isoformat(), "end": tdates[b].isoformat()} for a, b in events]
print("regional events:")
for e in ev_list:
    a = tdates.index(datetime.date.fromisoformat(e['onset']))
    b = tdates.index(datetime.date.fromisoformat(e['end']))
    print("  ", e['onset'], "->", e['end'], f"({b-a+1} d), active days: {int(active[a:b+1].sum())}")

np.save('work/mask.npy', mask)
with open('work/events.json', 'w') as f:
    json.dump(ev_list, f)
print("done", time.time()-t0)
