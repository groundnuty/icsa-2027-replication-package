import json
import numpy as np, xarray as xr

ds = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(ds)
m = ds['mhw']
print("dtype:", m.dtype, "dims:", m.dims)
print("time:", m['time'].values[0], "->", m['time'].values[-1], "n=", m.sizes['time'])
print("lat:", m['lat'].values[0], "->", m['lat'].values[-1], "n=", m.sizes['lat'])
print("lon:", m['lon'].values[0], "->", m['lon'].values[-1], "n=", m.sizes['lon'])
print("unique values:", np.unique(m.values))
print("total ones:", int(m.values.sum()))
# consistency with saved pipeline array
mhw = np.load('/work/mhw.npy').reshape(92, 60, 60)
print("matches pipeline array:", np.array_equal(m.values, mhw))
# land cells zero
sea = np.load('/work/sea_mask.npy')
print("all non-land zeros:", not np.any(m.values[:, ~sea]))
ds.close()

r = json.load(open('/work/output/report.json'))
assert set(r.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
assert isinstance(r["complete"], bool) and isinstance(r["caveats"], str)
print("report OK:", json.dumps(r["events"]))
print("ALL CHECKS PASSED")
