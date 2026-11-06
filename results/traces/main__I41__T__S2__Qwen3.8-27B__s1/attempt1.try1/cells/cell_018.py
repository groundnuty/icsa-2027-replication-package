import numpy as np, pandas as pd, json, time
t0=time.time()
zt = np.load("work/target.npz"); tc = np.load("work/thrclim.npz")
sst_t = zt["sst"]            # (92, 60, 60) float64
time_arr = zt["time"]; sea = zt["sea"]
THR = tc["THR"]              # (366, 3600) smoothed

# target day-of-year (2021 non-leap; mapping is calendar-based so same as leap layout)
dates = pd.DatetimeIndex(time_arr.astype("datetime64[D]"))
doy_target = np.array([(pd.Timestamp(2004, int(m), int(d)) - pd.Timestamp(2004,1,1)).days + 1
                       for m, d in zip(dates.month, dates.day)], dtype=int)
print("doy target first/last:", doy_target[0], doy_target[-1], "expect 152..243:", (doy_target[0], doy_target[-1]) == (152,243))

sst3 = sst_t.reshape(92, -1)
thr3 = THR[:, :3600]
hot = (sst3 >= thr3[doy_target - 1][:, :])   # (92, 3600); land: thr NaN -> False
print("hot days total:", int(hot.sum()), " per-cell max hot:", int(hot.sum(axis=0).max()))

C = 3600
mhw = np.zeros((92, C), dtype=np.uint8)
ncell_events = 0
for c in range(C):
    if not sea.flat[c]:
        continue
    h = hot[:, c]
    # find runs of consecutive hot days
    runs = []
    i = 0
    while i < 92:
        if h[i]:
            j = i
            while j + 1 < 92 and h[j+1]:
                j += 1
            if j - i + 1 >= 5:
                runs.append([i, j])
            i = j + 1
        else:
            i += 1
    # join runs separated by 1-2 non-hot days
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    if merged:
        ncell_events += 1
    for s, e in merged:
        mhw[s:e+1, c] = 1

mhw = mhw.reshape(92, 60, 60)
active = mhw.astype(bool).any(axis=(1,2))
print("days with any cell in MHW:", int(active.sum()), "of 92")
print("cells with >=1 per-cell MHW:", ncell_events, "of sea cells 3308")

# regional events: maximal runs of consecutive active days
events = []
i = 0
while i < 92:
    if active[i]:
        j = i
        while j + 1 < 92 and active[j+1]:
            j += 1
        events.append((str(dates[i].date()), str(dates[j].date())))
        i = j + 1
    else:
        i += 1
print("regional events:", events)
np.save("work/mhw.npy", mhw)
json.dump({"events": events, "active": [str(dates[i].date()) for i in range(92) if active[i]]}, open("work/events.json","w"), indent=1)
print("time", round(time.time()-t0,1), "s")
