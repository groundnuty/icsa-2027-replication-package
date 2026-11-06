import xarray as xr, numpy as np, json
ds = xr.open_dataset('output/mhw_mask.nc', engine='netcdf4')
print(ds)
m = ds['mhw']
print("dtype:", m.dtype, "dims:", m.dims, "shape:", m.shape)
print("unique values:", np.unique(m.values))
print("mhw cell-days:", int(m.values.sum()))
# land cells all zero?
sea = np.load('/tmp/stage2.npz')['sea']
print("land cells all 0:", bool((m.values[:, ~sea]==0).all()))
print("time:", str(ds.time.values[0])[:10], "..", str(ds.time.values[-1])[:10], len(ds.time.values))
print("lat:", float(ds.lat[0]), float(ds.lat[-1]), "lon:", float(ds.lon[0]), float(ds.lon[-1]))
ds.close()

rep = json.load(open('output/report.json'))
print(json.dumps(rep, indent=2))
keys = set(rep.keys())
assert keys == {"region","baseline_analysed","target_analysed","events","complete","caveats"}, keys
assert set(rep["region"]) == {"lat_min","lat_max","lon_min","lon_max"}
assert rep["events"][0]["onset"] <= rep["events"][0]["end"] <= rep["events"][1]["onset"] <= rep["events"][1]["end"]
print("report schema OK")
