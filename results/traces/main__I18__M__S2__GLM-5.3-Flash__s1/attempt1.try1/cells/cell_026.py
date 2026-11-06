import xarray as xr, numpy as np, json, os

ds = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
print(ds)
print("mhw dtype:", ds.mhw.dtype, "dims:", ds.mhw.dims)
print("time:", ds.time.values[0], "..", ds.time.values[-1], "n:", ds.sizes["time"])
print("lat:", ds.lat.values[[0,-1]], "lon:", ds.lon.values[[0,-1]])
m = ds.mhw.values
print("mhw sum:", m.sum(), "unique:", np.unique(m))
print("time values sample:", ds.time.values[:3], ds.time.values[-2:])

with open("output/report.json") as fh:
    rep = json.load(fh)
print(json.dumps(rep, indent=1)[:1600])
print("top-level keys:", sorted(rep.keys()))
print("files:", os.listdir("output"), [os.path.getsize("output/"+f) for f in os.listdir("output")])
ds.close()
