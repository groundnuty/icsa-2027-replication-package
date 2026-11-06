import numpy as np
z = np.load('/work/sst_region.npz', allow_pickle=False)
A = z['A']; dates = [str(d) for d in z['dates']]
d2i = {d: i for i, d in enumerate(dates)}
mdays = [31,29,31,30,31,30,31,31,30,31,30,31]
cum = [0]
for m in mdays: cum.append(cum[-1]+m)
def doy(s): return cum[int(s[5:7])-1] + int(s[8:10])
doy_all = np.array([doy(s) for s in dates])

tgt_s = d2i['2010-06-01']; tgt_e = d2i['2010-08-31'] + 1
tgt = A[tgt_s:tgt_e]              # (92,60,60)
tgt_dates = dates[tgt_s:tgt_e]
tdoy = doy_all[tgt_s:tgt_e]
print("target days:", len(tgt), tgt_dates[0], tgt_dates[-1], "doy:", tdoy.min(), tdoy.max())

tc = np.load('/work/thr_cli.npz', allow_pickle=False)
thr_s, cli_s = tc['thr_s'], tc['cli_s']

sea = np.all(np.isfinite(tgt), axis=0)   # (60,60)
sea_cells = np.argwhere(sea)
print("sea cells:", len(sea_cells))

# hot days: SST (K) >= smoothed threshold for that day of year
hot = np.zeros((len(tgt), len(sea_cells)), dtype=bool)
for t in range(len(tgt)):
    d = tdoy[t]
    thr_cell = thr_s[d]                 # (60,60)
    h = tgt[t] >= thr_cell
    hot[t] = h[sea]
print("total hot cell-days:", hot.sum(), " hot-day range:", hot.sum(axis=1).min(), hot.sum(axis=1).max())

# per-cell MHW: runs of >=5 consecutive hot days, merge gaps of 1-2 non-hot days
mask = np.zeros_like(hot)
ncells_with_mhw = 0
for c in range(len(sea_cells)):
    h = hot[:, c]
    # find hot runs
    runs = []
    i = 0
    n = len(h)
    while i < n:
        if h[i]:
            s = i
            while i < n and h[i]:
                i += 1
            runs.append((s, i-1))
        else:
            i += 1
    # keep runs >= 5
    cands = [(s, e) for (s, e) in runs if e - s + 1 >= 5]
    # merge with gap <= 2
    merged = []
    for (s, e) in cands:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    for (s, e) in merged:
        mask[s:e+1, c] = True
    if merged:
        ncells_with_mhw += 1
print("cells with >=1 MHW:", ncells_with_mhw)

active = mask.any(axis=1)
print("active days:", int(active.sum()), "of", len(active))
# regional events: maximal runs of consecutive active days
events = []
i = 0
while i < len(active):
    if active[i]:
        s = i
        while i < len(active) and active[i]:
            i += 1
        events.append((tgt_dates[s], tgt_dates[i-1]))
    else:
        i += 1
for e in events:
    print("event:", e[0], "->", e[1], "len", len(tgt_dates) and (int(tgt_dates.index(e[1])) - int(tgt_dates.index(e[0])) + 1))

np.savez_compressed('/work/mhw_intermediate.npz', mask=mask,
                    sea=sea, tgt_dates=np.array(tgt_dates),
                    events=np.array(events, dtype=object))
print("saved intermediate")
