import numpy as np, json, xarray as xr

ds = xr.open_dataset("/work/output/mhw_mask.nc", engine="h5netcdf")
print(ds)
m = ds["mhw"]
print("dtype:", m.dtype, "| dims:", m.dims, "| shape:", m.shape)
print("time:", str(ds["time"].values[0])[:10], "..", str(ds["time"].values[-1])[:10], "| n =", ds["time"].size)
print("lat:", float(ds["lat"].min()), "..", float(ds["lat"].max()), ds["lat"].dtype)
print("lon:", float(ds["lon"].min()), "..", float(ds["lon"].max()), ds["lon"].dtype)
print("mhw sum:", int(m.values.sum()), "| unique:", np.unique(m.values))

# cross-check against computed mask
zm = np.load("/work/cache_mhw.npz")
print("matches computed mhw exactly:", np.array_equal(m.values, zm["mhw"]))
active = m.values.reshape(m.shape[0], -1).any(axis=1)
print("active days:", int(active.sum()))

# report.json
with open("/work/output/report.json") as f:
    r = json.load(f)
print("report keys:", sorted(r.keys()))
assert sorted(r.keys()) == ["baseline_analysed", "caveats", "complete", "events", "region", "target_analysed"]
print("events:", r["events"], "| complete:", r["complete"])
print("ALL OUTPUT CHECKS PASSED")
