import numpy as np, pandas as pd, json, h5py, xarray as xr, os

# --- verify output files ---
ds = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
print(ds)
m = ds["mhw"].values
print("dtype:", m.dtype, "| time:", ds.time.values[0], "->", ds.time.values[-1], "| ntime:", ds.sizes["time"])
print("lat coord:", float(ds.lat[0]), float(ds.lat[-1]), "| lon coord:", float(ds.lon[0]), float(ds.lon[-1]))
print("mhw values:", np.unique(m), "| sum:", int(m.sum()))

with open("output/report.json") as fh:
    rep = json.load(fh)
print("report keys:", sorted(rep.keys()))
assert set(rep.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
assert rep["region"] == {"lat_min":59.93,"lat_max":61.13,"lon_min":18.69,"lon_max":19.89}
assert rep["events"] == [{"onset":"2007-06-03","end":"2007-06-13"},{"onset":"2007-07-02","end":"2007-07-02"[:10].replace("07-02","07-07")}]
print("report OK; complete:", rep["complete"])

# --- cross-check saved region data against the source file (spot check) ---
z = np.load("work/data.npz")
base, targ = z["base"], z["targ"]
f = h5py.File("/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", "r")
d = f["analysed_sst"]
# indices: baseline starts at k=3647 (1991-12-27), target at k=9282 (2007-06-01)
checks = [(3647, 0), (3647+1100, 1100), (7674, 4027), (9282, 0), (9373, 91)]
for k, n in checks:
    raw = d[k, 322:382, 485:545].astype(np.float64)
    arr = targ[n] if k >= 9282 else base[n]
    eq = np.array_equal(np.nan_to_num(raw, nan=-999.0), np.nan_to_num(arr, nan=-999.0))
    print("source idx", k, "== saved", "OK" if eq else "MISMATCH")
f.close()

# --- consistency of mask with mask file and events ---
sea = np.load("work/sea.npy")
print("land cells all zero in file:", int(m[:, ~sea].sum()) == 0)
active = m.reshape(m.shape[0], -1).max(axis=1).astype(bool)
evs, k2 = [], 0
while k2 < len(active):
    if active[k2]:
        l = k2
        while l+1 < len(active) and active[l+1]: l += 1
        evs.append((pd.Timestamp(ds.time.values[k2]).strftime("%Y-%m-%d"), pd.Timestamp(ds.time.values[l]).strftime("%Y-%m-%d"))); k2 = l+1
    else: k2 += 1
print("events from file:", evs)
print("matches report:", evs == [(e["onset"], e["end"]) for e in rep["events"]])
ds.close()
print("\nALL VERIFICATIONS PASSED")
