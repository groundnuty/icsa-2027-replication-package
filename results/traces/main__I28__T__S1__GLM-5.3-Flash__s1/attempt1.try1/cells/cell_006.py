import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
for nm in ['sst_20130601.nc','sst_19920101.nc','sst_19820101.nc']:
    with fs.open(f'{base}/{nm}','rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        print("=====", nm, "=====")
        v = ds['analysed_sst']
        print("encoding:", {k:v.encoding.get(k) for k in ('_FillValue','dtype','scale_factor','add_offset','units')})
        print("attrs:", v.attrs)
        print("time:", ds.time.values)
        lat = ds.latitude.values; lon = ds.longitude.values
        print("lat:", lat[0], lat[-1], len(lat), "step:", lat[1]-lat[0])
        print("lon:", lon[0], lon[-1], len(lon), "step:", lon[1]-lon[0])
        print("lat monotonic increasing:", np.all(np.diff(lat)>0), "lon:", np.all(np.diff(lon)>0))
        a = v.values[0]
        print("sst dtype:", a.dtype, "nan count:", np.isnan(a).sum(), "finite:", np.isfinite(a).sum())
        print("range finite:", np.nanmin(a), np.nanmax(a))
        # land mask around region
        ds.close()
