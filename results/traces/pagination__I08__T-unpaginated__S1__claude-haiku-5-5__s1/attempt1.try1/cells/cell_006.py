import fsspec, xarray as xr, numpy as np, time, os
fs = fsspec.filesystem('onedata')
def rd(d):
    p=f'icsa2027_data_20261101T090944Z/s1z/sst_{d}.nc'
    with fs.open(p,'rb') as f:
        ds=xr.open_dataset(f,engine='h5netcdf').load()
    la=ds.latitude.values; lo=ds.longitude.values
    il=np.where((la>=54.81-1e-4)&(la<=56.01+1e-4))[0]; jl=np.where((lo>=19.61-1e-4)&(lo<=20.81+1e-4))[0]
    sub=ds.analysed_sst.isel(time=0, latitude=il, longitude=jl).values.astype(np.float64)
    return sub, la[il], lo[jl]
t=time.time(); s,la,lo=rd('20070601'); print(time.time()-t, s.shape, la[[0,-1]], lo[[0,-1]], np.isfinite(s).mean())
os.makedirs('/tmp/x',exist_ok=True); open('/tmp/x/a','w').write('hi'); print(os.path.exists('/tmp/x/a'))
