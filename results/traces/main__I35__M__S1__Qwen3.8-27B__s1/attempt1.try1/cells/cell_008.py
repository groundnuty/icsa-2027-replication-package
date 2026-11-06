import h5py, numpy as np, time, json, datetime as dt

BASE = "/data/icsa2027_data_20261101T090944Z/s1z"
dates = json.load(open("/tmp/mhw/dates.json"))["base_win"]
nb = np.memmap("/tmp/mhw/baseline.npy", dtype=np.float64, mode="r+", shape=(len(dates), 3600))

def load_chunk(dsl, rows):
    t0 = time.time()
    for k, d in enumerate(dsl):
        p = f"{BASE}/sst_{d.replace('-','')}.nc"
        with h5py.File(p, "r") as f:
            sl = f["analysed_sst"][0, 322:382, 485:545][:]
        nb[rows[k]] = sl.astype(np.float64).ravel()
    nb.flush()
    return time.time() - t0

chunk, start = 800, 0
secs = load_chunk(dates[start:start+chunk], range(start, start+chunk))
print(f"rows {start}..{start+chunk}: {secs:.1f}s ({secs/chunk*1000:.0f} ms/file)")
