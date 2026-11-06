import xarray as xr, numpy as np, json
ds=xr.open_dataset('output/mhw_mask.nc')
print(ds)
m=ds['mhw']
print("dtype:", m.dtype, "shape:", m.shape, "sum:", int(m.values.sum()))
print("time:", ds.time.values[0], "->", ds.time.values[-1], "n:", ds.sizes['time'])
print("lat range:", float(ds.lat.min()), float(ds.lat.max()), "lon range:", float(ds.lon.min()), float(ds.lon.max()))
rep=json.load(open('output/report.json'))
print(json.dumps(rep, indent=2)[:1500])
assert set(rep)=={"region","baseline_analysed","target_analysed","events","complete","caveats"}
assert m.dtype==np.uint8 and set(m.dims)=={"time","lat","lon"}
print("ALL CHECKS PASSED")
