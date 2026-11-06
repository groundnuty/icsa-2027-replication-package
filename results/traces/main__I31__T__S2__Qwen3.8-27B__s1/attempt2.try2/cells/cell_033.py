import xarray as xr, json, os
import numpy as np

print("files:", os.path.getsize('/work/output/mhw_mask.nc'), "bytes,", os.path.getsize('/work/output/report.json'), "bytes")
ds = xr.open_dataset('/work/output/mhw_mask.nc')
print(ds)
m = ds.mhw.values
print("mhw dtype:", m.dtype, "shape:", m.shape, "sum:", int(m.sum()), "min:", int(m.min()), "max:", int(m.max()))
print("time:", str(ds.time.values[0])[:10], "..", str(ds.time.values[-1])[:10], "n=", len(ds.time))
print("lat:", float(ds.lat.values[0]), "..", float(ds.lat.values[-1]), "n=", len(ds.lat))
print("lon:", float(ds.lon.values[0]), "..", float(ds.lon.values[-1]), "n=", len(ds.lon))
# verify coords match source dataset exactly
fs = __import__('fsspec').filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
src = xr.open_dataset(f, engine='h5netcdf')
lat = src.latitude.values; lon = src.longitude.values
lm = (lat >= 58.69) & (lat <= 59.89); lom = (lon >= 18.69) & (lon <= 19.89)
print("lat coords match source:", np.array_equal(ds.lat.values, lat[lm].astype(np.float32)))
print("lon coords match source:", np.array_equal(ds.lon.values, lon[lom].astype(np.float32)))
tt = src.time.values
print("time coords match source:", np.array_equal(ds.time.values, tt[np.datetime64('2017-06-01'):np.datetime64('2017-09-01')]))

rep = json.load(open('/work/output/report.json'))
print("\nreport.json:")
print(json.dumps(rep, indent=1)[:1500])
print("\nfields:", sorted(rep.keys()))
