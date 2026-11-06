
import numpy as np, fsspec, xarray as xr
def load_day(p):
    return np.fromfile(p, dtype=np.float64).reshape(60,60)

fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z'
ok = True
for name in ['sst_20140601.nc','sst_19970101.nc','sst_19911227.nc','sst_20030105.nc','sst_20140831.nc']:
    dstr = name[4:-3]
    with fs.open(f'{base}/{name}','rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        ref = np.asarray(ds['analysed_sst'].values[0, 278:338, 613:673], dtype=np.float64)
    a = load_day(f'/work/ext/e_{dstr}.npy')
    same_nan = np.array_equal(np.isnan(a), np.isnan(ref))
    fin = np.isfinite(a)
    diff = float(np.abs(a[fin]-ref[fin]).max())
    print(name, "NaN pattern same:", same_nan, "max finite diff:", diff)
    ok &= same_nan and diff == 0.0
print("ALL EXACT:", ok)
