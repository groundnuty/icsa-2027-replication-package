import numpy as np, json, datetime as dt
raw = json.load(open("/tmp/mhw/dates.json"))
target = [dt.date.fromisoformat(x) for x in raw["target"]]
ntf  = np.asarray(np.memmap("/tmp/mhw/target.npy", dtype=np.float64, mode="r", shape=(92, 3600)))
thr_s = np.load("/tmp/mhw/thr_s.npy")
sea = np.all(np.isfinite(ntf), axis=0)
doy_t = np.array([d.timetuple().tm_yday for d in target])
hot = (ntf >= thr_s[doy_t - 1]) & sea[None, :]
hotdays = np.flatnonzero(hot.any(axis=1))
print("hot days (idx):", hotdays, "->", [target[i].isoformat() for i in hotdays])
