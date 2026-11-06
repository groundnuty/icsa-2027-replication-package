import h5py, numpy as np, time, json
BASE = "/data/icsa2027_data_20261101T090944Z/s1z"
td = json.load(open("/tmp/mhw/dates.json"))["target"]
nt = np.memmap("/tmp/mhw/target.npy", dtype=np.float64, mode="r+", shape=(len(td), 3600))
t0 = time.time()
for k, d in enumerate(td):
    with h5py.File(f"{BASE}/sst_{d.replace('-','')}.nc", "r") as f:
        sl = f["analysed_sst"][0, 322:382, 485:545][:]
    nt[k] = sl.astype(np.float64).ravel()
nt.flush()
print(f"target loaded in {time.time()-t0:.1f}s")

# quick sanity: sea cells (finite all 92 days)
ntf = np.asarray(nt)
sea = np.all(np.isfinite(ntf), axis=0)
print("sea cells:", sea.sum(), "of", len(sea))
perday_frac = np.isfinite(ntf).mean(axis=1)
print("min daily finite frac:", perday_frac.min())
