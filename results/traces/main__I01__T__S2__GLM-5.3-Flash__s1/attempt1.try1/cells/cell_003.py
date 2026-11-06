import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
sst = ds['analysed_sst']
print("encoding keys:", {k: v for k, v in sst.encoding.items() if k != 'coordinates'})

tvals = ds.time.values
lat = ds.latitude.values; lon = ds.longitude.values
latmask = (lat >= 54.13) & (lat <= 55.33); lonmask = (lon >= 14.67) & (lon <= 15.87)
lat_idx = np.where(latmask)[0]; lon_idx = np.where(lonmask)[0]
print("lat_idx contiguous:", np.all(np.diff(lat_idx)==1), "lon_idx contiguous:", np.all(np.diff(lon_idx)==1))

i0 = np.searchsorted(tvals, np.datetime64('2008-06-01'))
i1 = np.searchsorted(tvals, np.datetime64('2008-08-31'), 'right')
print("target index", i0, i1, tvals[i0], tvals[i1-1])

t0 = time.time()
slab = sst.isel(time=slice(i0,i1), latitude=slice(lat_idx[0], lat_idx[-1]+1), longitude=slice(lon_idx[0], lon_idx[-1]+1)).values
print("read time %.1fs shape %s dtype %s" % (time.time()-t0, slab.shape, slab.dtype))
print("finite fraction:", np.isfinite(slab).mean())
fin_days = np.isfinite(slab).sum(axis=0)
vals, cnts = np.unique(fin_days, return_counts=True)
print("finite-days histogram (value:count):", dict(zip(vals.tolist(), cnts.tolist())))
