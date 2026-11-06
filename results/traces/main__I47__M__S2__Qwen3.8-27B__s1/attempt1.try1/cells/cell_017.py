import numpy as np, json

z = np.load("work/sst.npz", allow_pickle=False)
tgt_dates = z["tgt_dates"].astype("datetime64[D]")
tgt64 = z["tgt_arr"].astype(np.float64).reshape(z["tgt_arr"].shape[0], -1)
st = np.load("work/stats.npz")
thr_s = st["thr_s"]; sea_idx = st["sea_idx"]

cum = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366])
def doy_of_np(d):
    m0 = int(np.datetime64(d, "M"))                     # 0-based month
    day = int(np.datetime64(d) - np.datetime64(d, "M")) + 1
    return cum[m0] + day
tgt_doy = np.array([doy_of_np(d) for d in tgt_dates])
print("target doys first/last:", tgt_doy[0], tgt_doy[-1], "n:", len(tgt_doy))
assert tgt_doy[0] == 153 and tgt_doy[-1] == 244 and len(tgt_doy) == 92
assert np.all(np.diff(tgt_doy) == 1)

n_sea = len(sea_idx)
thr_t = thr_s[:, tgt_doy - 1]      # (n_sea, 92)
sst_t = tgt64[:, sea_idx]          # (92, n_sea)
print("target NaN at sea cells:", int(np.isnan(sst_t).sum()))
hot = sst_t >= thr_t.T             # (92, n_sea)

mhw = np.zeros_like(hot)
n_mhw_cells = 0
for c in range(n_sea):
    h = hot[:, c]
    runs, i, n = [], 0, len(h)
    while i < n:
        if h[i]:
            j = i
            while j + 1 < n and h[j + 1]:
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
            merged.append(list(r))
    if merged:
        n_mhw_cells += 1
    for s, e in merged:
        mhw[s:e+1, c] = 1

print("cells with >=1 MHW:", n_mhw_cells, "of", n_sea)
print("MHW day-cells total:", int(mhw.sum()))

active = (mhw.sum(axis=1) > 0)
print("active days:", int(active.sum()), "of", len(active))
events = []
i, n = 0, len(active)
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
json.dump(events, open("work/events.json", "w"))
print("saved")
