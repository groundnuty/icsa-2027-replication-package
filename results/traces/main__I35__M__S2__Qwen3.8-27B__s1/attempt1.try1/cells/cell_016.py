import numpy as np

PREF = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
def doy(dates):
    dates = dates.astype("datetime64[D]")
    d = dates.astype("int64")
    first = dates.astype("datetime64[M]").astype("datetime64[D]").astype("int64")
    day = d - first + 1
    month = dates.astype("datetime64[M]").astype("int64") % 12
    return PREF[month] + day

X = np.load("/tmp/X.npy")
p3 = np.load("/tmp/p3.npy")
sea = np.load("/tmp/sea.npy")
M = np.load("/tmp/M.npy")
nsea = int(sea.sum())
Xsea = X[:, sea]

# threshold & climatology, rows 0..365 = doy 1..366
thr = np.full((366, nsea), np.nan)
clim = np.full((366, nsea), np.nan)
for d in range(1, 367):
    if d == 60: continue
    vals = Xsea[M[d-1]]
    thr[d-1] = np.nanquantile(vals, 0.9, axis=0, method="hazen")
    clim[d-1] = np.nanmean(vals, axis=0)
thr[59] = (thr[58] + thr[60]) / 2.0
clim[59] = (clim[58] + clim[60]) / 2.0
print("NaNs after fill: thr", int(np.isnan(thr).sum()), "clim", int(np.isnan(clim).sum()))

def smooth31(a):
    idx = (np.arange(366)[:, None] - 15 + np.arange(31)[None, :]) % 366
    return a[idx].mean(axis=1)
thr_s = smooth31(thr)
clim_s = smooth31(clim)
print("thr_s NaNs:", int(np.isnan(thr_s).sum()), " clim_s NaNs:", int(np.isnan(clim_s).sum()))
print("thr_s range: %.3f .. %.3f K  (%.2f .. %.2f C)" % (thr_s.min(), thr_s.max(), thr_s.min()-273.15, thr_s.max()-273.15))
print("clim_s range: %.3f .. %.3f K" % (clim_s.min(), clim_s.max()))

# target days
t0 = np.datetime64("2009-06-01")
tdates = t0 + np.arange(p3.shape[0])
tdoy = doy(tdates)
print("target doy range:", tdoy.min(), tdoy.max())

SST_t = p3[:, sea]  # (92, nsea), NaN where missing (shouldn't happen for sea cells)
print("target NaNs over sea cells:", int(np.isnan(SST_t).sum()))

hot = SST_t >= thr_s[tdoy - 1]   # (92, nsea)
print("hot fraction:", float(hot.mean()))

# per-cell MHW: runs >=5 hot days; join runs separated by <=2 non-hot days; gap days included
nt = p3.shape[0]
hpad = np.zeros((nsea, nt + 2), dtype=bool); hpad[:, 1:-1] = hot.T
diff = np.diff(hpad.astype(np.int8), axis=1)
mhw = np.zeros((nt, nsea), dtype=bool)
n_mhw_cells = 0
durs = []
for c in range(nsea):
    starts = np.where(diff[c] == 1)[0]     # hpad index of first hot day
    ends = np.where(diff[c] == -1)[0]      # hpad index of last hot day
    runs = [(s, e) for s, e in zip(starts, ends) if e - s + 1 >= 5]
    if not runs: continue
    merged = [list(runs[0])]
    for s, e in runs[1:]:
        if s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    for s, e in merged:
        mhw[s-1:e, c] = True
    n_mhw_cells += len(merged)
    durs += [e - s + 1 for s, e in merged]

print("cells with >=1 MHW:", int(mhw.any(axis=0).sum()), " total per-cell MHWs:", n_mhw_cells)
print("MHW duration distribution:", {k: v for k, v in sorted(np.unique(durs).tolist())})

active = mhw.any(axis=1)
print("active days:", int(active.sum()), "of", nt)

# regional events: maximal runs of consecutive active days
dura = np.diff(np.concatenate([[0], active.astype(int), [0]]))
ev_s = np.where(dura == 1)[0]
ev_e = np.where(dura == -1)[0] - 1
events = [(tdates[s], tdates[e]) for s, e in zip(ev_s, ev_e)]
print("regional events:")
for s, e in events:
    print("  ", str(s), "->", str(e), " len", (e - s).astype(int) + 1)

np.save("/tmp/thr_s.npy", thr_s); np.save("/tmp/clim_s.npy", clim_s)
np.save("/tmp/mhw.npy", mhw.astype(np.uint8))
np.save("/tmp/tdoy.npy", tdoy)
import json
json.dump([{"onset": str(s), "end": str(e)} for s, e in events], open("/tmp/events.json", "w"))
print("OK")
