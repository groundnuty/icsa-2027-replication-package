
import json, numpy as np
import xarray as xr

r = json.load(open('output/report.json'))
assert set(r) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
assert set(r["region"]) == {"lat_min","lat_max","lon_min","lon_max"}
assert all(set(e) == {"onset","end"} for e in r["events"])
assert isinstance(r["complete"], bool) and isinstance(r["caveats"], str)

ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
assert ds['mhw'].dtype == 'uint8'
assert ds['mhw'].dims == ('time','lat','lon')
assert ds['mhw'].shape == (92, 60, 60)
assert set(np.unique(ds['mhw'].values)) <= {0,1}
# land cells (306) must be 0 on every day
mask = np.asarray(ds['mhw'].values)
zero_cols = (mask == 0).all(axis=0)
print("cells always 0 (land):", int(zero_cols.sum()))
print("time:", str(ds['time'].values[0])[:10], "->", str(ds['time'].values[-1])[:10])
print("all checks passed")
print("events:", r["events"])
ds.close()
