import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

with fs.open(f'{base}/sst_20220601.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds.latitude.values.astype(np.float64)
    lon = ds.longitude.values.astype(np.float64)
    print('lat step:', np.unique(np.round(np.diff(lat),6))[:5])
    print('lon step:', np.unique(np.round(np.diff(lon),6))[:5])
    print('analysed_sst attrs:', ds.analysed_sst.attrs)
    # region selection with tolerance
    lat0, lat1, lon0, lon1 = 54.81, 56.01, 19.61, 20.81
    tol = 1e-3
    latm = (lat >= lat0 - tol) & (lat <= lat1 + tol)
    lonm = (lon >= lon0 - tol) & (lon <= lon1 + tol)
    print('n lat:', latm.sum(), 'n lon:', lonm.sum())
    latr = lat[latm]; lonr = lon[lonm]
    print('lat range:', latr[0], latr[-1])
    print('lon range:', lonr[0], lonr[-1])
    i0 = np.where(latm)[0][0]; i1 = np.where(latm)[0][-1]
    j0 = np.where(lonm)[0][0]; j1 = np.where(lonm)[0][-1]
    print('indices', i0, i1, j0, j1)
    # check values in region
    sub = ds.analysed_sst[0, i0:i1+1, j0:j1+1].values.astype(np.float64)
    print('sub shape', sub.shape, 'finite frac', np.isfinite(sub).mean(), 'min/max', np.nanmin(sub), np.nanmax(sub))
    # how many cells NaN
    print('n nan cells:', (~np.isfinite(sub)).sum())

t0=time.time()
for d in ['19911227','19920601','20030106','20220831']:
    with fs.open(f'{base}/sst_{d}.nc','rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        v = ds.analysed_sst[0, i0:i1+1, j0:j1+1].values.astype(np.float64)
print('4 opens+reads secs:', time.time()-t0)
