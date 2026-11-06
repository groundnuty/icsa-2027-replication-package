import numpy as np, fsspec, xarray as xr
z = np.load('work/sst.npz')
ST, SB = z['ST'], z['SB']
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
dlat, dlon, dt = ds.latitude.values, ds.longitude.values, ds.time.values
eps = 1e-6
li = np.where((dlat >= 54.17-eps) & (dlat <= 55.37+eps))[0]
lo = np.where((dlon >= 13.25-eps) & (dlon <= 14.45+eps))[0]
def idx(ts): return int(np.searchsorted(dt, np.datetime64(ts)))
checks = [('2004-08-01', idx('2004-06-01'), ST, 92), ('2004-07-31', idx('2004-06-01'), ST, 92),
          ('2004-06-01', idx('2004-06-01'), ST, 92), ('1996-07-17', idx('1991-12-27'), SB, 4028),
          ('1992-01-01', idx('1991-12-27'), SB, 4028), ('2002-12-31', idx('1991-12-27'), SB, 4028)]
ok = True
for dstr, base, arr, n in checks:
    i = idx(dstr); rel = i - base
    ref = arr[rel].astype(np.float64)
    fresh = ds['analysed_sst'].isel(time=i, latitude=slice(int(li[0]),int(li[-1])+1), longitude=slice(int(lo[0]),int(lo[-1])+1)).values.astype(np.float64)
    fm = np.isfinite(ref)
    bit_equal = float((fresh[fm] == ref[fm]).mean())
    nan_match = float((np.isnan(fresh) == np.isnan(ref)).mean())
    maxd = float(np.abs(fresh[fm] - ref[fm]).max())
    print(dstr, "finite bit-equal frac:", bit_equal, "| max finite diff:", maxd, "| NaN pattern match:", nan_match)
    ok &= (bit_equal == 1.0 and nan_match == 1.0 and maxd == 0.0)
print("ALL READS VERIFIED:", ok)
