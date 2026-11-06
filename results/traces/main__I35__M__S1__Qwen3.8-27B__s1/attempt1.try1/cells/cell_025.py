import xarray as xr, numpy as np, json
ds = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
m = ds["mhw"]
print(m.dtype, m.dims, m.shape)
print("time:", str(ds["time"].values[0]), "->", str(ds["time"].values[-1]))
print("lat:", float(ds["lat"].values[0]), float(ds["lat"].values[-1]),
      " lon:", float(ds["lon"].values[0]), float(ds["lon"].values[-1]))
perday = m.values.sum(axis=(1, 2))
nz = np.flatnonzero(perday)
print("active days:", len(nz), "first/last idx:", nz[0], nz[-1])
# check contiguity -> events
gaps = np.flatnonzero(np.diff(nz) > 1)
print("event boundaries (idx):", np.split(nz, gaps+1))
print("values unique:", np.unique(m.values))
ds.close()
print(json.load(open("output/report.json"))["events"])
