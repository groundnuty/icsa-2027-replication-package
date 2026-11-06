import xarray as xr, numpy as np, json, pickle
ds = xr.open_dataset('output/mhw_mask.nc', engine='netcdf4')
print(ds)
print("mhw dtype:", ds.mhw.dtype, "| dims:", ds.mhw.dims, "| shape:", ds.mhw.shape)
with open('/tmp/stepB2.pkl','rb') as fh: B = pickle.load(fh)
print("values identical to computed mask:", np.array_equal(ds.mhw.values.astype(np.uint8), B['mhw']))
print("ones:", int(ds.mhw.values.sum()), "| time:", str(ds.time.values[0])[:10], "->", str(ds.time.values[-1])[:10], "n =", ds.sizes['time'])
print("lat:", float(ds.lat[0]), "..", float(ds.lat[-1]), "| lon:", float(ds.lon[0]), "..", float(ds.lon[-1]))
with open('output/report.json') as fh: rep = json.load(fh)
print("report keys:", sorted(rep.keys()))
print("events:", rep["events"], "| complete:", rep["complete"])
import os
print("file sizes:", os.path.getsize('output/mhw_mask.nc'), os.path.getsize('output/report.json'))
