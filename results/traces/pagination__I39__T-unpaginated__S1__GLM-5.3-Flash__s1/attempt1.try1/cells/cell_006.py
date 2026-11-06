import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z/sst_20100601.nc'
with fs.open(p, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print(ds.analysed_sst.encoding)
    print(ds.analysed_sst.attrs)
    lat = ds.latitude.values
    lon = ds.longitude.values
    print(lat[:5], lat[-5:])
    print(lon[:5], lon[-5:])
    sst = ds.analysed_sst.isel(time=0).values
    print('nan frac', np.isnan(sst).mean())
    print('min/max', np.nanmin(sst), np.nanmax(sst))
    # region selection
    latf = np.round(lat.astype('float64'), 2)
    lonf = np.round(lon.astype('float64'), 2)
    latmask = (latf >= 60.49) & (latf <= 61.69)
    lonmask = (lonf >= 17.25) & (lonf <= 18.45)
    print('nlat', latmask.sum(), 'nlon', lonmask.sum())
    print(latf[latmask][:3], latf[latmask][-3:])
    print(lonf[lonmask][:3], lonf[lonmask][-3:])
    sub = sst[np.ix_(latmask, lonmask)]
    print('sub nan frac', np.isnan(sub).mean())
    print('sub min/max', np.nanmin(sub), np.nanmax(sub))
