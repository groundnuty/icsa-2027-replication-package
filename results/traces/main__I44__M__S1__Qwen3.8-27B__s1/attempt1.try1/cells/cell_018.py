import xarray as xr, json, numpy as np

ds = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
print(ds)
m = ds["mhw"]
print("dtype:", m.dtype, "dims:", dict(m.sizes))
print("time[0], time[-1]:", ds.time.values[0], ds.time.values[-1])
print("lat:", ds.lat.values[0], "->", ds.lat.values[-1], "| lon:", ds.lon.values[0], "->", ds.lon.values[-1])
print("mhw sum:", int(m.values.sum()), "| days with any 1:", int((m.values.sum(axis=(1,2)) > 0).sum()))
print("per-day counts:", [int(x) for x in m.values.sum(axis=(1,2)) if x > 0])
# verify land cells are 0 and no 1 outside target
lat_ok = (ds.lat.values >= 63.31) & (ds.lat.values <= 64.51)
lon_ok = (ds.lon.values >= 21.31) & (ds.lon.values <= 22.51)
print("lat/lon bounds respected:", bool(lat_ok.all() and lon_ok.all()))
print("mhw values set:", np.unique(m.values))
ds.close()
print()
print(open("output/report.json").read())
