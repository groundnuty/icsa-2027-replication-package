import xarray as xr, numpy as np, json

ds = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
print(ds)
v = ds["mhw"]
print("dtype:", v.dtype, "dims:", v.dims)
print("mhw sum:", int(v.values.sum()), "unique:", np.unique(v.values))
print("time range:", ds.time.values[0], ds.time.values[-1], "n:", ds.time.size)
print("lat:", ds.lat.values[0], ds.lat.values[-1], "n:", ds.lat.size)
print("lon:", ds.lon.values[0], ds.lon.values[-1], "n:", ds.lon.size)
# day-level counts matching events
days = ds.time.dt.strftime("%Y-%m-%d").values
import collections
cnt = collections.Counter()
for i in range(v.time.size):
    s = int(v.values[i].sum())
    if s: cnt[days[i]] = s
print("active days/cells:", dict(sorted(cnt.items())))
ds.close()

r = json.load(open("output/report.json"))
print(json.dumps(r, indent=1)[:1200])
assert set(r.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
print("report keys OK")
