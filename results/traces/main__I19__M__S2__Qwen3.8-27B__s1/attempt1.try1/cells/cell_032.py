import xarray as xr, json, numpy as np
ds = xr.open_dataset('/work/output/mhw_mask.nc', engine="h5netcdf")
print(ds)
print("mhw dtype:", ds.mhw.dtype)
m = ds.mhw.values
print("values unique:", np.unique(m))
print("sum:", int(m.sum()))
print("time[0], time[-1]:", ds.time[0].values, ds.time[-1].values, "len", len(ds.time))
print("lat range:", ds.lat.values[0], ds.lat.values[-1], " n=", len(ds.lat))
print("lon range:", ds.lon.values[0], ds.lon.values[-1], " n=", len(ds.lon))
print("lat dtype:", ds.lat.dtype, "lon dtype:", ds.lon.dtype)
# cross-check against stored mem
M = np.load('/work/mhw.npz', allow_pickle=True)
mem = M['mem']
assert m.shape == (92, 60, 60)
assert np.array_equal(m, mem.reshape(92,60,60).astype(np.uint8)), "mask mismatch"
print("mask matches in-memory computation: True")
# day of event start (idx 53) and a random day
print("rows with any=1:", np.where(m.any(axis=(1,2)))[0])
print(json.dumps(json.load(open('/work/output/report.json')), indent=2))
