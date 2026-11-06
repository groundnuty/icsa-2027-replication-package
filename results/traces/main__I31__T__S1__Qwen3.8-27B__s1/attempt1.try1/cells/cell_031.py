
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
def open_day(path, eng='h5netcdf'):
    f = fs.open(path, 'rb')
    return xr.open_dataset(f, engine=eng)

# load a 1982 day from s1z (per-day file)
ds1 = open_day('/icsa2027_data_20261101T090944Z/s1z/sst_19820715.nc')
print("s1z vars:", list(ds1.variables), ds1.analysed_sst.shape if 'analysed_sst' in ds1 else [v for v in ds1.variables])
v1 = ds1[list(ds1.data_vars)[0]] if not 'analysed_sst' in ds1 else ds1.analysed_sst
lat1 = np.asarray(ds1[v1.dims[1]].values, dtype=np.float64) if len(v1.dims)==2 else None
print("s1z dims:", v1.dims, v1.dtypes if hasattr(v1,'dtypes') else v1.dtype)
print("s1z attrs:", {k: v for k, v in v1.attrs.items()})
print("s1z coords:", {c: (str(ds1[c].values[0]), str(ds1[c].values[-1]), len(ds1[c])) for c in ds1.coords})
ds1.close()
