import numpy as np, json
from collections import Counter

PREF = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
def doy(dates):
    dates = dates.astype("datetime64[D]")
    d = dates.astype("int64")
    first = dates.astype("datetime64[M]").astype("datetime64[D]").astype("int64")
    day = d - first + 1
    month = dates.astype("datetime64[M]").astype("int64") % 12
    return PREF[month] + day

X = np.load("/tmp/X.npy")      # 1991-12-27..2003-01-05, (4028, 3600)
p3 = np.load("/tmp/p3.npy")    # 2009-06-01..2009-08-31, (92, 3600)
sea = np.load("/tmp/sea.npy")  # (3600,)
M = np.load("/tmp/M.npy")      # (366, 4028)
nsea = int(sea.sum())
Xsea = X[:, sea]

# ---- thresholds & climatology (row = doy-1) ----
thr = np.full((366, nsea), np.nan)
clim = np.full((366, nsea), np.nan)
for d in range(1, 367):
    if d == 60: continue
    vals = Xsea[M[d-1]]
    thr[d-1] = np.nanquantile(vals, 0.9, axis=0, method="hazen")
    clim[d-1] = np.nanmean(vals, axis=0)
thr[59] = (thr[58] + thr[60]) / 2.0
clim[59] = (clim[58] + clim[60]) / 2.0
assert not np.isnan(thr).any() and not np.isnan(clim).any()

idx = (np.arange(366)[:, None] - 15 + np.arange(31)[None, :]) % 366
thr_s = thr[idx].mean(axis=1)
clim_s = clim[idx].mean(axis=1)
assert not np.isnan(thr_s).any()

# ---- target period ----
tdates = np.datetime64("2009-06-01") + np.arange(p3.shape[0])
tdoy = doy(tdates)
SST_t = p3[:, sea]
assert not np.isnan(SST_t).any()
hot = SST_t >= thr_s[tdoy - 1]

# ---- per-cell MHWs ----
nt = p3.shape[0]
mhw = np.zeros((nt, nsea), dtype=bool)
durs = []
for c in range(nsea):
    hpad = np.array([False] + list(hot[:, c]) + [False])
    d = np.diff(hpad.astype(np.int8))
    starts = np.where(d == 1)[0]; ends = np.where(d == -1)[0]
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
        durs.append(e - s + 1)

print("hot fraction: %.4f" % float(hot.mean()))
print("cells with >=1 MHW:", int(mhw.any(axis=0).sum()), "of", nsea)
print("per-cell MHWs:", len(durs), "durations:", dict(sorted(Counter(durs).items())))

active = mhw.any(axis=1)
print("active days:", int(active.sum()), "of", nt)
dd = np.diff(np.concatenate([[0], active.astype(int), [0]]))
ev_s = np.where(dd == 1)[0]; ev_e = np.where(dd == -1)[0] - 1
events = [(int(s), int(e)) for s, e in zip(ev_s, ev_e)]
print("regional events:")
for s, e in events:
    print("   %s -> %s  len %d" % (str(tdates[s]), str(tdates[e]), e - s + 1))

np.save("/tmp/thr_s.npy", thr_s); np.save("/tmp/clim_s.npy", clim_s)
np.save("/tmp/mhw.npy", mhw.astype(np.uint8))
np.save("/tmp/tdates.npy", tdates.astype("datetime64[D]").astype("int64"))
json.dump([{"onset": str(tdates[s]), "end": str(tdates[e])} for s, e in events], open("/tmp/events.json", "w"))
print("saved OK")
