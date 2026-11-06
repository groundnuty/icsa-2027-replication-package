import fsspec, traceback
import numpy as np, xarray as xr

fs = fsspec.filesystem('onedata')
cands = ['icsa2027_data_20261101T090944Z/s2z/sst_s2.nc',
         '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc']
f = None
for p in cands:
    try:
        f = fs.open(p, 'rb'); print("opened:", p); break
    except Exception as e:
        print("fail:", p, repr(e)[:200])
if f is None:
    raise SystemExit("could not open file")

ds = xr.open_dataset(f, engine='h5netcdf')
print(str(ds)[:5000])
print("---- data vars ----")
for name in list(ds.data_vars):
    v = ds[name]
    print("VAR", name, v.dims, v.dtype, {k: v.attrs[k] for k in list(v.attrs)[:5]})
main = 'analysed_sst' if 'analysed_sst' in ds.data_vars else list(ds.data_vars)[0]
enc = ds[main].encoding
print("ENC", main, {k: enc.get(k) for k in ('chunks','chunksizes','dtype','_FillValue','scale_factor','add_offset','compressor','filters','source')})
