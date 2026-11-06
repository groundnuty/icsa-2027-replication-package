import xarray, json, numpy as np
ds = xarray.open_dataset("output/mhw_mask.nc")
print(ds)
v = ds.mhw
print("dtype:", v.dtype, "dims:", v.dims)
print("time n:", v.sizes["time"], "first/last:", ds.time.values[0], ds.time.values[-1])
print("lat n:", v.sizes["latitude"], "min/max:", float(ds.latitude.values.min()), float(ds.latitude.values.max()))
print("lon n:", v.sizes["longitude"], "min/max:", float(ds.longitude.values.min()), float(ds.longitude.values.max()))
print("mhw unique:", np.unique(v.values), "sum:", int(v.values.sum()))
assert v.dtype == np.uint8
assert v.dims == ("time", "latitude", "longitude")
# every coordinate within region bounds
assert (ds.latitude.values >= 54.13).all() and (ds.latitude.values <= 55.33).all()
assert (ds.longitude.values >= 14.67).all() and (ds.longitude.values <= 15.87).all()
assert (ds.time.values >= np.datetime64("2004-06-01")).all() and (ds.time.values <= np.datetime64("2004-08-31")).all()
assert len(np.unique(ds.time.values)) == 92
r = json.load(open("output/report.json"))
assert set(r.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
assert r["region"] == {"lat_min":54.13,"lat_max":55.33,"lon_min":14.67,"lon_max":15.87}
assert r["baseline_analysed"] == {"start":"1991-12-27","end":"2003-01-05"}
assert r["target_analysed"] == {"start":"2004-06-01","end":"2004-08-31"}
assert r["events"] == [] and r["complete"] is True and isinstance(r["caveats"], str)
print("ALL CHECKS PASSED")
import os
for f in ["output/mhw_mask.nc", "output/report.json"]:
    print(f, os.path.getsize(f), "bytes")
