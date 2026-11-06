import h5py, numpy as np, time, json
BASE = "/data/icsa2027_data_20261101T090944Z/s1z"
dates = json.load(open("/tmp/mhw/dates.json"))["base_win"]
nb = np.memmap("/tmp/mhw/baseline.npy", dtype=np.float64, mode="r+", shape=(len(dates), 3600))

def load_chunk(dsl, rows):
    t0 = time.time()
    for k, d in enumerate(dsl):
        with h5py.File(f"{BASE}/sst_{d.replace('-','')}.nc", "r") as f:
            sl = f["analysed_sst"][0, 322:382, 485:545][:]
        nb[rows[k]] = sl.astype(np.float64).ravel()
    nb.flush()
    return time.time() - t0

s = 800
secs = load_chunk(dates[s:s+1600], range(s, s+1600))
print(f"rows {s}..{s+1600}: {secs:.1f}s")
