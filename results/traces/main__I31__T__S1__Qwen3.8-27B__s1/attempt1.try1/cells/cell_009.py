
import fsspec, xarray as xr, numpy as np, time, psutil
fs = fsspec.filesystem('onedata')
f = fs.open('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print("time[0], time[-1]:", ds.time.values[0], ds.time.values[-1])
print("lat range:", float(ds.latitude.values[0]), float(ds.latitude.values[-1]), "n=", len(ds.latitude))
print("lon range:", float(ds.longitude.values[0]), float(ds.longitude.values[-1]), "n=", len(ds.longitude))
# region indices
lat = np.asarray(ds.latitude.values, dtype=np.float64)
lon = np.asarray(ds.longitude.values, dtype=np.float64)
latm = (lat >= 58.69) & (lat <= 59.89)
lonm = (lon >= 18.69) & (lon <= 19.89)
print("region lat vals:", lat[latm][0], lat[latm][-1], "n=", latm.sum())
print("region lon vals:", lon[lonm][0], lon[lonm][-1], "n=", lonm.sum())
print("analyse_sst units:", ds.analysed_sst.attrs.get('units'))
print("decode_cf attrs:", ds.attrs.get('comment'))
t0 = time.time()
# small read test: one day, region
idx_t = np.datetime64('1992-01-01')
i0 = np.searchsorted(ds.time.values, idx_t)
print("idx of 1992-01-01:", i0, ds.time.values[i0])
chunk = ds.analysed_sst.isel(time=i0, latitude=np.where(latm)[0], longitude=np.where(lonm)[0]).values
print("read time:", time.time()-t0, "s; chunk:", chunk.shape, chunk.dtype, "finite:", np.isfinite(chunk).sum())
print("sample values (K):", chunk.ravel()[:8])
ds.close()
