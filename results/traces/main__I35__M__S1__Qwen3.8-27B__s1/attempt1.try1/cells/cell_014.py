import numpy as np, json, datetime as dt
np.seterr(all="ignore")

raw = json.load(open("/tmp/mhw/dates.json"))
target = [dt.date.fromisoformat(x) for x in raw["target"]]
ntf  = np.asarray(np.memmap("/tmp/mhw/target.npy", dtype=np.float64, mode="r", shape=(92, 3600)))
thr_s = np.load("/tmp/mhw/thr_s.npy")

sea = np.all(np.isfinite(ntf), axis=0)
print("sea cells:", int(sea.sum()))

doy_t = np.array([d.timetuple().tm_yday for d in target])
# hot: SST (K) >= threshold for that day of year; only sea cells can be hot
hot = (ntf >= thr_s[doy_t - 1]) & sea[None, :]
print("total hot cell-days:", int(hot.sum()), " max per day:", int(hot.max(axis=1).sum()))

T, C = hot.shape
inmhw = np.zeros((T, C), dtype=np.uint8)
n_cells_mhw = 0
for c in np.flatnonzero(sea):
    h = hot[:, c]
    if not h.any():
        continue
    d = np.diff(h.astype(np.int8))
    starts = np.flatnonzero(d == 1)
    ends   = np.flatnonzero(d == -1) - 1
    runs = [(s, e) for s, e in zip(starts, ends) if e - s + 1 >= 5]
    if not runs:
        continue
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    n_cells_mhw += 1
    for s, e in merged:
        inmhw[s:e+1, c] = 1

print("cells with >=1 MHW:", n_cells_mhw)
active = inmhw.any(axis=1)
print("active days:", int(active.sum()))

events = []
d = np.diff(active.astype(np.int8))
starts = np.flatnonzero(d == 1); ends = np.flatnonzero(d == -1) - 1
if active[0]: starts = np.concatenate(([0], starts))
if active[-1]: ends = np.concatenate((ends, [T-1]))
for s, e in zip(starts, ends):
    events.append({"onset": target[s].isoformat(), "end": target[e].isoformat()})
print("events:", json.dumps(events))
np.save("/tmp/mhw/inmhw.npy", inmhw)
json.dump(events, open("/tmp/mhw/events.json", "w"))
