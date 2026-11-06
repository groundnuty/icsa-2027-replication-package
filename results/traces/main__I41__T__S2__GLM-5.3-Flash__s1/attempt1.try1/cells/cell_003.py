import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds['latitude'].values.astype(np.float64)
    lon = ds['longitude'].values.astype(np.float64)
    # values near bounds
    for name, arr, lo, hi in [("lat", lat, 61.57, 62.77), ("lon", lon, 20.17, 21.37)]:
        near = arr[(arr > lo-0.06) & (arr < hi+0.06)]
        print(name, "near-bounds values:", np.round(near, 6))
    latm = (lat >= 61.57) & (lat <= 62.77)
    lonm = (lon >= 20.17) & (lon <= 21.37)
    ilat = np.where(latm)[0]; ilon = np.where(lonm)[0]
    print("n lat cells:", len(ilat), "range idx", ilat[0], ilat[-1], "vals", lat[ilat[0]], lat[ilat[-1]])
    print("n lon cells:", len(ilon), "range idx", ilon[0], ilon[-1], "vals", lon[ilon[0]], lon[ilon[-1]])
    print("n cells:", len(ilat)*len(ilon))

    # timing: read one day's full spatial chunk
    t0 = time.time()
    v = ds['analysed_sst'].isel(time=0).values
    t1 = time.time()
    print("read day0 full slice: %.2f s" % (t1-t0), v.shape, "finite frac:", np.isfinite(v).mean())
    t0 = time.time()
    v2 = ds['analysed_sst'].isel(time=15000).values
    t1 = time.time()
    print("read day15000 full slice: %.2f s" % (t1-t0), "finite frac:", np.isfinite(v2).mean())
    # region subset of a middle day
    t0 = time.time()
    sub = ds['analysed_sst'].isel(time=7300, latitude=ilat, longitude=ilon).values
    t1 = time.time()
    print("region-subset read: %.2f s" % (t1-t0), sub.shape, "finite frac:", np.isfinite(sub).mean(), "mean K:", np.nanmean(sub))
