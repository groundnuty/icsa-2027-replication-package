import numpy as np, json, datetime as dt
np.seterr(all="ignore")
raw = json.load(open("/tmp/mhw/dates.json"))
target = [dt.date.fromisoformat(x) for x in raw["target"]]
ntf  = np.asarray(np.memmap("/tmp/mhw/target.npy", dtype=np.float64, mode="r", shape=(92, 3600)))
thr_s = np.load("/tmp/mhw/thr_s.npy")

sea = np.all(np.isfinite(ntf), axis=0)
doy_t = np.array([d.timetuple().tm_yday for d in target])
hot = (ntf >= thr_s[doy_t - 1]) & sea[None, :]

T, C = hot.shape
inmhw = np.zeros((T, C), dtype=np.uint8)
n_cells_mhw = 0
for c in np.flatnonzero(sea):
    h = hot[:, c]
    if not h.any():
        continue
    D = np.diff(np.concatenate(([0], h.astype(np.int8), [0])))
    starts = np.flatnonzero(D == 1)
    ends   = np.flatnonzero(D == -1) - 1
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
print("active days:", int(active.sum()), "->", [target[i].isoformat() for i in np.flatnonzero(active)])

D2 = np.diff(np.concatenate(([0], active.astype(np.int8), [0])))
starts = np.flatnonzero(D2 == 1); ends = np.flatnonzero(D2 == -1) - 1
events = [{"onset": target[s].isoformat(), "end": target[e].isoformat()} for s, e in zip(starts, ends)]
print("events:", json.dumps(events))
np.save("/tmp/mhw/inmhw.npy", inmhw)
json.dump(events, open("/tmp/mhw/events.json", "w"))
