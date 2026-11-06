import numpy as np, xarray as xr, json, pandas as pd

o = xr.open_dataset('/work/output/mhw_mask.nc')
src = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
i0 = int(np.searchsorted(src.time.values, np.datetime64('2014-06-01')))
assert np.array_equal(o.time.values, src.time.values[i0:i0+92])
assert np.array_equal(o.lat.values, src.latitude.values[np.flatnonzero((src.latitude.values>=54.17)&(src.latitude.values<=55.37))])
assert np.array_equal(o.lon.values, src.longitude.values[np.flatnonzero((src.longitude.values>=13.25)&(src.longitude.values<=14.45))])

flat = o.mhw.values.reshape(92, -1).any(axis=1)
ev = []
td = pd.to_datetime(o.time.values)
i = 0
while i < 92:
    if flat[i]:
        j = i
        while j+1 < 92 and flat[j+1]: j += 1
        ev.append((str(td[i].date()), str(td[j].date()))); i = j+1
    else: i += 1
print("events re-derived from output file:", ev)

r = json.load(open('/work/output/report.json'))
assert set(r.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
assert [(e["onset"], e["end"]) for e in r["events"]] == ev
assert r["complete"] is True and isinstance(r["caveats"], str)
assert r["region"] == {"lat_min":54.17,"lat_max":55.37,"lon_min":13.25,"lon_max":14.45}
assert r["baseline_analysed"] == {"start":"1991-12-27","end":"2003-01-05"}
assert r["target_analysed"] == {"start":"2014-06-01","end":"2014-08-31"}
print("report.json consistent with mask file")
print("ALL CHECKS PASSED")
import os
for f in ['/work/output/mhw_mask.nc','/work/output/report.json']:
    print(f, os.path.getsize(f), "bytes")
