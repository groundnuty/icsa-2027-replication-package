import xarray as xr, numpy as np, json
ds = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
print(ds)
m = ds["mhw"]
print("dtype:", m.dtype, "| dims:", m.dims, "| shape:", m.shape)
print("time:", str(ds.time.values[0])[:10], "->", str(ds.time.values[-1])[:10], "n =", ds.sizes["time"])
print("lat:", ds.lat.values[0], "..", ds.lat.values[-1], "n =", ds.sizes["lat"])
print("lon:", ds.lon.values[0], "..", ds.lon.values[-1], "n =", ds.sizes["lon"])
print("mhw sum:", int(m.values.sum()), "| unique:", np.unique(m.values))
ref = np.load("/tmp/mhw_mask.npy")
print("matches computed mask:", np.array_equal(m.values, ref.astype(np.uint8)))
rep = json.load(open("output/report.json"))
print("report keys:", sorted(rep.keys()))
print("events:", rep["events"], "| complete:", rep["complete"])
