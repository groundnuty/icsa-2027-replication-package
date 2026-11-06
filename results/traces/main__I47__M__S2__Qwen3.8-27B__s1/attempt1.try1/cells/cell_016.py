import numpy as np

z = np.load("work/sst.npz", allow_pickle=False)
tgt_dates = z["tgt_dates"].astype("datetime64[D]")
tgt64 = z["tgt_arr"].astype(np.float64).reshape(z["tgt_arr"].shape[0], -1)
st = np.load("work/stats.npz")
thr_s = st["thr_s"]; sea_idx = st["sea_idx"]

# day-of-year for each target date (2019 non-leap; June..Aug => 153..244)
tgt_doy = np.array([int(np.datetime_as_string(d, unit="D") and 0) for d in tgt_dates])  # placeholder
from datetime import date
tgt_doy = np.array([ (lambda m, d: 0 if False else 0)(1,1) for _ in tgt_dates])  # redo properly below
cum = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366])
tgt_doy = np.array([cum[int(np.datetime64(d).astype("datetime64[M]")) and 0] for d in tgt_dates])  # placeholder
# proper: parse month/day
tgt_doy = np.array([cum[d.astype("datetime64[M]").astype(int) % 12] + int(d.astype("datetime64[D]") - d.astype("datetime64[M]")) + 1
                    for d in tgt_dates])
# careful: cum[m] is end-of-month; doy = cum[m-1] + day. m = month index 0-based
def doy_of_np(d):
    m0 = int(np.datetime64(d, "M"))            # 0-based month
    day = int(np.datetime64(d) - np.datetime64(d, "M")) + 1
    return cum[m0] + day
tgt_doy = np.array([doy_of_np(d) for d in tgt_dates])
print("target doys first/last:", tgt_doy[0], tgt_doy[-1], "n:", len(tgt_doy))
assert tgt_doy[0] == 153 and tgt_doy[-1] == 244 and len(tgt_doy) == 92
assert np.all(np.diff(tgt_doy) == 1)

n_sea = len(sea_idx)
thr_t = thr_s[:, tgt_doy - 1]                      # (n_sea, 92)
sst_t = tgt64[:, sea_idx]                          # (92, n_sea)
hot = sst_t >= thr_t.T                             # (92, n_sea); NaN>=x -> False, but sea cells have no NaN in target

# verify no NaN in target for sea cells
print("target NaN at sea cells:", int(np.isnan(sst_t).sum()))

# per-cell: find hot runs, keep len>=5, merge if gap in {1,2}
mhw = np.zeros_like(hot)
run_lengths = []
for c in range(n_sea):
    h = hot[:, c]
    # maximal runs of 1s
    runs = []
    i = 0
    n = len(h)
    while i < n:
        if h[i]:
            j = i
            while j + 1 < n and h[j + 1]:
                j += 1
            runs.append([i, j])
            i = j + 1
        else:
            i += 1
    runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
    # merge
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] - 1 <= 2:
            merged[-1][1] = r[1]
        else:
            merged.append(list(r))
    for s, e in merged:
        mhw[s:e+1, c] = 1
        run_lengths.append(e - s + 1)

print("cells with >=1 MHW:", int((mhw.sum(axis=0) > 0).sum()))
print("MHW day-cells total:", int(mhw.sum()))

active = (mhw.sum(axis=1) > 0)
print("active days:", int(active.sum()), "of", len(active))
# regional events: maximal runs of consecutive active days
events = []
i = 0
n = len(active)
while i < n:
    if active[i]:
        j = i
        while j + 1 < n and active[j + 1]:
            j += 1
        events.append((str(tgt_dates[i]), str(tgt_dates[j])))
        i = j + 1
    else:
        i += 1
for e in events:
    print("event:", e[0], "->", e[1])

np.savez_compressed("work/mhw.npz", mhw=mhw, tgt_dates=tgt_dates, active=active)
import json
json.dump(events, open("work/events.json", "w"))
print("saved")
