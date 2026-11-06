import numpy as np, h5py, time, os, datetime as dt
p='/data/icsa2027_data_20261101T090944Z/s1z/sst_20040615.nc'
with h5py.File(p,'r') as f:
    print(list(f.keys()))
    def show(name,obj):
        if isinstance(obj,h5py.Dataset):
            print(name, obj.shape, obj.dtype, dict(obj.attrs))
    f.visititems(show)
    lat=f['latitude'][:]
    lon=f['longitude'][:]
    sst=f['analysed_sst']
    print('sst attrs', sst.attrs)
    # find indices
    i0=np.searchsorted(lat,57.57-1e-6); i1=np.searchsorted(lat,58.77+1e-6)
    j0=np.searchsorted(lon,10.25-1e-6); j1=np.searchsorted(lon,11.45+1e-6)
    print('idx',i0,i1,j0,j1)
    t0=time.time()
    blk=sst[0,i0:i1,j0:j1]
    print('read %.3fs'%(time.time()-t0), blk.dtype, blk.shape, np.isfinite(blk).mean())

# benchmark xarray vs h5py on 5 files
D='/data/icsa2027_data_20261101T090944Z/s1z'
import xarray as xr
for name in ['sst_19920601.nc','sst_19960229.nc','sst_20021231.nc','sst_19911227.nc','sst_20030105.nc']:
    fp=os.path.join(D,name)
    t0=time.time()
    with h5py.File(fp,'r') as f:
        lat2=f['latitude'][i0:i1]; lon2=f['longitude'][j0:j1]
        blk=f['analysed_sst'][0,i0:i1,j0:j1]
        tt=f['time'][:]
    t1=time.time()-t0
    t0=time.time()
    with xr.open_dataset(fp,engine='h5netcdf') as ds:
        sub=ds['analysed_sst'].sel(latitude=slice(57.57,58.77),longitude=slice(10.25,11.45)).values
        tv=ds['time'].values[0]
    t2=time.time()-t0
    print(name,'h5py %.3fs xr %.3fs'%(t1,t2),'grid same:',np.array_equal(lat2,lat) and np.array_equal(lon2,lon),'time',tv, 'finite frac %.3f'%np.isfinite(blk).mean())
