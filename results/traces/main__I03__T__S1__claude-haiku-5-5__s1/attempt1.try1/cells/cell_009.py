import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
with fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb') as f:
    d=xr.open_dataset(f,engine='h5netcdf')
    lat=d.latitude.values.astype(np.float64); lon=d.longitude.values.astype(np.float64)
    li=np.where((lat>=54.17)&(lat<=55.37))[0]; lo=np.where((lon>=13.25)&(lon<=14.45))[0]
    print(lat[li[0]],lat[li[-1]],len(li), lon[lo[0]],lon[lo[-1]],len(lo))
    sub=d.isel(latitude=slice(li[0],li[-1]+1), longitude=slice(lo[0],lo[-1]+1))
    base=sub.sel(time=slice('1991-12-27','2003-01-05')).analysed_sst.load()
    tgt=sub.sel(time=slice('2014-06-01','2014-08-31')).analysed_sst.load()
print(base.shape, tgt.shape, base.time.values[[0,-1]], tgt.time.values[[0,-1]])
print(float(np.nanmin(tgt)), float(np.nanmax(tgt)), np.isnan(tgt.values).sum(axis=0).max(), np.isfinite(tgt.values).all(axis=0).sum())