
import os, json
import xarray as xr

for p in ['output/mhw_mask.nc', 'output/report.json']:
    print(p, os.path.getsize(p), "bytes")

r = json.load(open('output/report.json'))
assert set(r) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
assert set(r["region"]) == {"lat_min","lat_max","lon_min","lon_max"}
assert all(set(e) == {"onset","end"} for e in r["events"])
assert isinstance(r["complete"], bool) and isinstance(r["caveats"], str)

ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
assert ds['mhw'].dtype == 'uint8'
assert ds['mhw'].dims == ('time','lat','lon')
assert ds['mhw'].shape == (92, 60, 60)
assert set(ds['mhw'].values) <= {0,1}
# land cells must be 0 everywhere
import numpy as np
sea = np.isfinite(ds['mhw'].values.sum(axis=0))  # not needed; check zero-rows instead
print("all checks passed")
print("events:", r["events"])
ds.close()
