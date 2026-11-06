import fsspec,xarray as xr,pandas as pd,numpy as np,os,time,glob
fs=fsspec.filesystem('onedata')
D='icsa2027_data_20261101T090944Z/s1z'
for f in bad:
    d=f[-11:-3];t=f'/work/t_{d}.nc'
    fs.get(f'{D}/sst_{d}.nc',t)
    x=xr.open_dataset(t,engine='h5netcdf')
    x=x.sel(latitude=slice(64.35,65.65),longitude=slice(23.35,24.65)).load()
    x.to_netcdf(f);x.close();os.remove(t)
fl=sorted(glob.glob('/work/c/*.nc'))
A=[];T=[]
for f in fl:
    x=xr.open_dataset(f,engine='h5netcdf')
    A.append(x.analysed_sst.values[0]);T.append(x.time.values[0]);lat=x.latitude.values;lon=x.longitude.values;x.close()
A=np.array(A);t=pd.DatetimeIndex(T)
print(A.shape,(t==pd.to_datetime([f[-11:-3] for f in fl])).all(),np.nanmin(A),np.nanmax(A),A.dtype)
li=np.where((lat>=64.39-1e-4)&(lat<=65.59+1e-4))[0];lj=np.where((lon>=23.41-1e-4)&(lon<=24.61+1e-4))[0]
print(lat[li][[0,-1]],lon[lj][[0,-1]],len(li),len(lj))
np.save('/work/sst.npy',A[:,li[0]:li[-1]+1,lj[0]:lj[-1]+1].astype('float64'))
np.save('/work/t.npy',t.values);np.save('/work/lat.npy',lat[li]);np.save('/work/lon.npy',lon[lj])