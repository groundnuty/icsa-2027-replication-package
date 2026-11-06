
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
f = fs.open('/icsa2027_data_20261101T090944Z/s1z/sst_19820715.nc', 'rb')
ds1 = xr.open_dataset(f, engine='h5netcdf')
a1 = ds1.analysed_sst.values.astype(np.float64)[0]   # (626, 1051)
ds1.close()
lat = np.load('work/lat.npy'); lon = np.load('work/lon.npy')
latm = (lat.astype(np.float64) >= 58.69) & (lat.astype(np.float64) <= 59.89)
lonm = (lon.astype(np.float64) >= 18.69) & (lon.astype(np.float64) <= 19.89)
li = np.where(latm)[0]; oi = np.where(lonm)[0]
sub1 = a1[li][:, oi]

f = fs.open('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds2 = xr.open_dataset(f, engine='h5netcdf')
i = int(np.searchsorted(ds2.time.values, np.datetime64('1982-07-15')))
a2 = ds2.analysed_sst.isel(time=i, latitude=li, longitude=oi).values.astype(np.float64)
ds2.close()
d = sub1 - a2
print("shape:", sub1.shape, "identical:", bool((sub1 == a2).all()))
print("n NaN s1z:", int(np.isnan(sub1).sum()), " n NaN s2z:", int(np.isnan(a2).sum()))
fin = np.isfinite(d)
print("max abs diff (finite):", float(np.abs(d)[fin].max()) if fin.any() else 'n/a', " n finite:", int(fin.sum()))
print("sample s1z:", sub1.ravel()[:5], " sample s2z:", a2.ravel()[:5])
