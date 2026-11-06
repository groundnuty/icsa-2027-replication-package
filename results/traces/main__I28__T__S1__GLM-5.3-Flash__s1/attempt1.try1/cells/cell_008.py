import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
latmin, latmax, lonmin, lonmax = 57.85, 59.05, 21.01, 22.21

t0 = time.time()
with fs.open(f'{base}/sst_20130601.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds.latitude.values.astype('float64'); lon = ds.longitude.values.astype('float64')
    li = np.where((lat >= latmin-1e-9) & (lat <= latmax+1e-9))[0]
    oi = np.where((lon >= lonmin-1e-9) & (lon <= lonmax+1e-9))[0]
    sub = ds.analysed_sst.isel(time=0, latitude=li, longitude=oi).values.astype('float64')
    ds.close()
print("read time: %.2fs" % (time.time()-t0), "shape:", sub.shape, "finite:", np.isfinite(sub).sum())
print(sub[:2,:3])

# test 3 sequential + check per-file land mask variation
t0=time.time()
finites = []
for nm in ['sst_19920601.nc','sst_19920602.nc','sst_19920603.nc']:
    with fs.open(f'{base}/{nm}','rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        s = ds.analysed_sst.isel(time=0, latitude=li, longitude=oi).values.astype('float64')
        ds.close()
    finites.append(np.isfinite(s))
    print(nm, "finite:", int(finites[-1].sum()), "range:", np.nanmin(s), np.nanmax(s))
print("3 reads: %.2fs" % (time.time()-t0))
print("same finite mask:", np.array_equal(finites[0], finites[1]) and np.array_equal(finites[1], finites[2]))
