import os, json
import numpy as np, xarray as xr

for p in ['/work/output/mhw_mask.nc', '/work/output/report.json']:
    print(p, "exists:", os.path.exists(p), "size:", os.path.getsize(p))

# relative path check (cwd=/work)
print("output/mhw_mask.nc exists:", os.path.exists('output/mhw_mask.nc'))

with open('/work/output/report.json') as f:
    r = json.load(f)
required = ["region", "baseline_analysed", "target_analysed", "events", "complete", "caveats"]
print("fields exact:", sorted(r.keys()) == sorted(required))
print("region ok:", r["region"] == {"lat_min": 54.45, "lat_max": 55.65, "lon_min": 16.05, "lon_max": 17.25})
print("baseline:", r["baseline_analysed"], "target:", r["target_analysed"])
print("events:", r["events"])
print("complete:", r["complete"], "caveats:", repr(r["caveats"]))

ds = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print("\nfinal NC: dims", dict(ds.sizes), "mhw dtype", ds.mhw.dtype)
print("time:", ds.time.values[0], "...", ds.time.values[-1])
print("lat:", float(ds.lat[0]), "...", float(ds.lat[-1]), "| lon:", float(ds.lon[0]), "...", float(ds.lon[-1]))
print("mhw sum:", int(ds.mhw.values.sum()), "| per-day min/max:", int(ds.mhw.values.reshape(92,-1).sum(axis=1).min()), int(ds.mhw.values.reshape(92,-1).sum(axis=1).max()))
ds.close()
print("\nALL DELIVERABLES IN PLACE")
