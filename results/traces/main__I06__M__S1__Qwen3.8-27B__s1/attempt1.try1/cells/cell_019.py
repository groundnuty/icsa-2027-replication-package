import numpy as np, datetime as dt, json, os

TC = np.load("/tmp/mhw/thrcli.npz"); THR = TC["THR"]
Z = np.load("/tmp/mhw/loaded.npz"); Vt = Z["Vt"]
sea = TC["sea"]
TG_START = dt.date(2012,6,1)
tgt_dates = [TG_START + dt.timedelta(days=i) for i in range(92)]
leap_month = [31,29,31,30,31,30,31,31,30,31,30,31]
doy_of = {}
for m in range(1,13):
    s = 1
    for mm in range(1,m): s += leap_month[mm-1]
    for day in range(1, leap_month[m-1]+1):
        doy_of[(m,day)] = s + day - 1
tdoy = np.array([doy_of[(dd.month,dd.day)] for dd in tgt_dates])
print("target doy range:", tdoy.min(), tdoy.max())

hot = np.zeros((92, 60, 60), dtype=bool)
for i, d in enumerate(tdoy):
    hot[i] = Vt[i] >= THR[d-1]     # NaN -> False
hot &= sea
print("hot days total:", int(hot.sum()), " (max possible:", int((92*sea.sum())), ")")

n_t = 92
mask = np.zeros((n_t, 60, 60), dtype=bool)   # per-cell MHW membership incl. gap days
n_cell_mhws = 0
for r in range(60):
    for c in range(60):
        if not sea[r, c]:
            continue
        h = hot[:, r, c]
        # find maximal hot runs
        runs = []
        i = 0
        while i < n_t:
            if h[i]:
                j = i
                while j + 1 < n_t and h[j+1]:
                    j += 1
                runs.append([i, j])
                i = j + 1
            else:
                i += 1
        evs = [run for run in runs if run[1] - run[0] + 1 >= 5]
        # merge events separated by 1 or 2 days (gap days are non-hot automatically)
        merged = []
        for ev in evs:
            if merged and ev[0] - merged[-1][1] - 1 <= 2:
                merged[-1][1] = ev[1]
            else:
                merged.append(ev)
        for a, b in merged:
            mask[a:b+1, r, c] = True
            n_cell_mhws += 1
print("per-cell MHW count (after joining):", n_cell_mhws)

active = mask.any(axis=(1,2))
# regional events: maximal runs of consecutive active days
events = []
i = 0
while i < n_t:
    if active[i]:
        j = i
        while j + 1 < n_t and active[j+1]:
            j += 1
        events.append((tgt_dates[i].isoformat(), tgt_dates[j].isoformat()))
        i = j + 1
    else:
        i += 1
print("regional events:", events)
print("active days:", int(active.sum()))
print("per-cell mhw day counts min/max over cells with events:",
      int(mask.sum(axis=(1,2)).min()), int(mask.sum(axis=(1,2)).max()))

np.save("/tmp/mhw/mask.npy", mask.astype(np.uint8))
print("mask saved")
