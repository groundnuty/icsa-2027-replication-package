import xarray as xr, json, numpy as np, os
ds = xr.open_dataset('output/mhw_mask.nc')
print(ds)
print("mhw dtype:", ds['mhw'].dtype, "| dims order:", ds['mhw'].dims)
print("time:", ds.time.values[0], "...", ds.time.values[-1], "n:", len(ds.time), "monotonic:", bool((np.diff(ds.time.values) > 0).all()))
print("lat:", float(ds.lat.values[0]), "->", float(ds.lat.values[-1]), "n:", len(ds.lat), "dtype:", ds.lat.dtype)
print("lon:", float(ds.lon.values[0]), "->", float(ds.lon.values[-1]), "n:", len(ds.lon), "dtype:", ds.lon.dtype)
print("mhw min/max:", int(ds.mhw.min()), int(ds.mhw.max()), "all uint8 ok:", ds.mhw.dtype == np.uint8)
# verify coords match dataset source values
z = np.load('work/sst.npz')
assert (ds.lat.values == z['lat']).all() and (ds.lon.values == z['lon']).all()
assert (ds.time.values == z['tt'].astype('datetime64[ns]')).all()
print("coords identical to dataset values: OK")
rep = json.load(open('output/report.json'))
assert set(rep.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
assert set(rep["region"].keys()) == {"lat_min","lat_max","lon_min","lon_max"}
assert isinstance(rep["events"], list) and rep["events"] == []
assert rep["complete"] is True and isinstance(rep["caveats"], str)
print("report.json schema OK")
print("sizes:", os.path.getsize('output/mhw_mask.nc'), os.path.getsize('output/report.json'), "bytes")
print("ALL OUTPUTS VALIDATED")
