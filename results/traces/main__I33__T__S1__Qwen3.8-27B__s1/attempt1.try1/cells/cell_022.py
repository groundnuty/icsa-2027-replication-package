
import numpy as np, fsspec, xarray as xr
def load_day(p):
    return np.fromfile(p, dtype=np.float64).reshape(60,60)

a = load_day('/work/ext/e_20140601.npy')
print("2014-06-01:", a.shape, "finite:", np.isfinite(a).sum(), "min/max:", a[np.isfinite(a)].min(), a[np.isfinite(a)].max())
b = load_day('/work/ext/e_19920101.npy')
print("1992-01-01:", "finite:", np.isfinite(b).sum(), "min/max:", b[np.isfinite(b)].min(), b[np.isfinite(b)].max())

# cross-check with a fresh remote read
fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z'
with fs.open(f'{base}/sst_20140601.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    ref = np.asarray(ds['analysed_sst'].values[0, 278:338, 613:673], dtype=np.float64)
print("max abs diff vs fresh read:", np.abs(a-ref).max())

# also spot-check a winter file
with fs.open(f'{base}/sst_19970101.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    ref2 = np.asarray(ds['analysed_sst'].values[0, 278:338, 613:673], dtype=np.float64)
c = load_day('/work/ext/e_19970101.npy')
print("max abs diff 1997-01-01:", np.abs(c-ref2).max())
print("1997-01-01 finite:", np.isfinite(c).sum(), "min/max:", c[np.isfinite(c)].min(), c[np.isfinite(c)].max())
