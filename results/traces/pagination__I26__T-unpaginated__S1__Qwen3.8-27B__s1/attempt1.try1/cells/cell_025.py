import xarray as xr, json, numpy as np
ds = xr.open_dataset('/work/output/mhw_mask.nc', engine="h5netcdf")
print(ds)
print("dims:", dict(ds.sizes))
print("mhw dtype:", ds.mhw.dtype)
print("time[0], time[-1]:", ds.time.values[0], ds.time.values[-1], "n:", ds.time.size)
print("lat:", float(ds.lat.values[0]), "->", float(ds.lat.values[-1]), "n:", ds.lat.size)
print("lon:", float(ds.lon.values[0]), "->", float(ds.lon.values[-1]), "n:", ds.lon.size)
print("mhw per day (active days):")
perday = ds.mhw.values.sum(axis=(1,2))
for t, c in enumerate(perday):
    if c: print(" ", ds.time.values[t], int(c))
rep = json.load(open('/work/output/report.json'))
print(json.dumps(rep, indent=2))
# verify report region matches task, and that mask covers exactly the region cells & target days
assert set(ds.dims) == {'time','lat','lon'}
assert ds.mhw.dims == ('time','lat','lon')
assert ds.mhw.dtype == np.uint8
assert ds.time.size == 92 and ds.lat.size == 60 and ds.lon.size == 60
assert float(ds.lat.min()) >= 57.83 and float(ds.lat.max()) <= 59.03
assert float(ds.lon.min()) >= 17.41 and float(ds.lon.max()) <= 18.61
print("ALL OUTPUT CHECKS PASSED")
