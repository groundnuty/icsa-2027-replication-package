import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
t0=time.time()
with fs.open(f'{base}/sst_20070601.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    v = ds['analysed_sst']
    print('units', v.attrs.get('units'), 'dtype', v.dtype, 'encoding', {k:v.encoding[k] for k in ['dtype','scale_factor','add_offset','_FillValue'] if k in v.encoding})
    print('lat attrs', ds.latitude.attrs, 'lon attrs', ds.longitude.attrs)
    lat = ds.latitude.values.astype('float64'); lon = ds.longitude.values.astype('float64')
    latm = (lat >= 57.83) & (lat <= 59.03)
    lonm = (lon >= 17.41) & (lon <= 18.61)
    print('nlat', latm.sum(), 'nlon', lonm.sum(), 'lat bounds', lat[latm][0], lat[latm][-1], 'lon bounds', lon[lonm][0], lon[lonm][-1])
    sub = v.isel(time=0).isel(latitude=latm, longitude=lonm).values
    t1=time.time()
    print('sub shape', sub.shape, 'read time', t1-t0)
    print('finite frac', np.isfinite(sub).mean())
    print('sample', sub[0,:5])
    print('min/max', np.nanmin(sub), np.nanmax(sub))
    print('total time', time.time()-t0)
