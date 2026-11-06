
import xarray as xr, json, numpy as np
ds = xr.open_dataset('output/mhw_mask.nc')
print(ds)
print("mhw dtype:", ds.mhw.dtype, "dims:", dict(ds.mhw.sizes))
print("time[0], time[-1]:", ds.time.values[0], ds.time.values[-1])
print("lat:", ds.latitude.values[0], "->", ds.latitude.values[-1], "n:", len(ds.latitude))
print("lon:", ds.longitude.values[0], "->", ds.longitude.values[-1], "n:", len(ds.longitude))
m = ds.mhw.values
print("unique:", np.unique(m))
per_day = m.sum(axis=(1,2))
act = np.where(per_day>0)[0]
print("active day indices:", act[0], "..", act[-1], "count:", len(act))
# land cells must be all-zero; sea cells finite count
print("all-zero columns (land):", int((m.sum(axis=(0,1))==0).sum()))
with open('output/report.json') as f:
    rep = json.load(f)
print("json keys:", list(rep.keys()))
print("events:", rep["events"])
import os
for p in ['output/mhw_mask.nc','output/report.json']:
    print(p, os.path.getsize(p), "bytes")
