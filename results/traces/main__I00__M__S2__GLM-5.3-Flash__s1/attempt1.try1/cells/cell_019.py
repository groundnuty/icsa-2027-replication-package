script = r'''
import numpy as np, pickle, json, datetime as dtm

sst = np.load("/tmp/mhw_work/sst.npy").astype("float64")   # (4840, 60, 60)
targ_pos = np.load("/tmp/mhw_work/targ_pos.npy")           # (92,)
thresh = np.load("/tmp/mhw_work/thresh.npy")               # (366, 60, 60)
meta = pickle.load(open("/tmp/mhw_work/meta.pkl", "rb"))
ordered = meta["ordered"]
target_md = meta["target_md"]

MDAYS = [31,29,31,30,31,30,31,31,30,31,30,31]
CUM = [0]
for nd in MDAYS: CUM.append(CUM[-1]+nd)

# target dates and doys
targ_dates = ["2004-%02d-%02d" % (m, d) for (m, d) in target_md]
targ_doy = np.array([CUM[m-1]+d for (m, d) in target_md])
print("target first/last:", targ_dates[0], targ_dates[-1], "doy:", targ_doy[0], targ_doy[-1], "n:", len(targ_dates))

sst_t = sst[targ_pos]                       # (92, 60, 60)
thr_t = thresh[targ_doy - 1]                # (92, 60, 60)
hot = sst_t >= thr_t                        # NaN comparisons -> False
hot_finite = np.isfinite(sst_t) & np.isfinite(thr_t)
hot = np.where(hot_finite, hot, False)
print("total hot cell-days:", int(hot.sum()))

nlat, nlon = hot.shape[1], hot.shape[2]
mhw_mask = np.zeros_like(hot, dtype=bool)

def find_runs(bool_arr):
    # maximal runs of True: list of (start, end) inclusive indices
    runs = []
    n = len(bool_arr)
    i = 0
    while i < n:
        if bool_arr[i]:
            j = i
            while j + 1 < n and bool_arr[j+1]:
                j += 1
            runs.append((i, j))
            i = j + 1
        else:
            i += 1
    return runs

n_cells_with_mhw = 0
mhw_len_hist = {}
for i in range(nlat):
    for j in range(nlon):
        h = hot[:, i, j]
        if not h.any():
            continue
        runs = [r for r in find_runs(h) if r[1] - r[0] + 1 >= 5]
        if not runs:
            continue
        # join runs separated by 1 or 2 non-hot days
        merged = [list(runs[0])]
        for (s, e) in runs[1:]:
            gap = s - merged[-1][1] - 1
            if gap in (1, 2):
                merged[-1][1] = e
            else:
                merged.append([s, e])
        for (s, e) in merged:
            mhw_mask[s:e+1, i, j] = True
            L = e - s + 1
            mhw_len_hist[L] = mhw_len_hist.get(L, 0) + 1
        n_cells_with_mhw += 1

print("cells with >=1 per-cell MHW:", n_cells_with_mhw)
print("total MHW cell-days:", int(mhw_mask.sum()))
print("per-cell MHW length histogram (days: count):", dict(sorted(mhw_len_hist.items())))

# regional: active day = any cell in per-cell MHW
active = mhw_mask.any(axis=(1, 2))
print("active days:", int(active.sum()), "of", len(active))
print("active day flags:", "".join("1" if a else "." for a in active))

events = []
i = 0
while i < len(active):
    if active[i]:
        j = i
        while j + 1 < len(active) and active[j+1]:
            j += 1
        events.append((i, j))
        i = j + 1
    else:
        i += 1
print("regional events (abs idx):", events)
ev_str = [{"onset": targ_dates[s], "end": targ_dates[e]} for (s, e) in events]
print(json.dumps(ev_str, indent=1))

np.save("/tmp/mhw_work/mhw_mask.npy", mhw_mask)
with open("/tmp/mhw_work/events.json", "w") as f:
    json.dump(ev_str, f)
print("saved mask and events")
'''
open("/tmp/mhw_work/detect.py", "w").write(script)
exec(open("/tmp/mhw_work/detect.py").read())
