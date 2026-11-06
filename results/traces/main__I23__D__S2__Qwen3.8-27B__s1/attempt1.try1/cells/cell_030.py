import json
import xarray as xr
import numpy as np

ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(ds)
v = ds['mhw']
print("var:", v.name, "dtype:", v.dtype, "dims:", v.dims)
assert v.dtype == np.uint8
assert tuple(v.dims) == ('time','lat','lon')
assert v.shape == (92, 60, 60)
assert int(v.sum()) == 5
assert set(np.unique(v.values)) <= {0,1}
# coordinates match dataset values
ref = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat_ref = ref.latitude.values[196:256]; lon_ref = ref.longitude.values[485:545]
t_ref = ref.time.values[11474:11566]
assert np.array_equal(ds.lat.values, lat_ref.astype(ds.lat.dtype)) or np.array_equal(ds.lat.values.astype(np.float32), lat_ref)
assert np.array_equal(ds.lon.values.astype(np.float32), lon_ref)
assert np.array_equal(ds.time.values, t_ref)
print("coord check OK")
one = np.argwhere(v.values == 1)
print("ones at (t, lat, lon idx):", one)
print("date:", ds.time.values[one[0,0]], "lat:", ds.lat.values[one[0,1]], "lon:", ds.lon.values[one[0,2]])

rep = json.load(open('output/report.json'))
assert set(rep.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
assert set(rep["region"].keys()) == {"lat_min","lat_max","lon_min","lon_max"}
assert set(rep["baseline_analysed"].keys()) == {"start","end"}
assert set(rep["target_analysed"].keys()) == {"start","end"}
for e in rep["events"]:
    assert set(e.keys()) == {"onset","end"}
assert isinstance(rep["complete"], bool) and isinstance(rep["caveats"], str)
print("report fields OK")
print(json.dumps(rep["events"]))
