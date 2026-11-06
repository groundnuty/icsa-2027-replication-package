import fsspec,xarray as xr,pandas as pd,numpy as np,os,glob
fs=fsspec.filesystem('onedata')
D='icsa2027_data_20261101T090944Z/s1z'
fl=sorted(glob.glob('/work/c/*.nc'))
A=np.load('/work/sst.npy');t=pd.DatetimeIndex(np.load('/work/t.npy'));e=pd.to_datetime([f[-11:-3] for f in fl])
for i in np.where(t!=e)[0]:
    d=fl[i][-11:-3];tt=f'/work/t_{d}.nc'
    fs.get(f'{D}/sst_{d}.nc',tt)
    x=xr.open_dataset(tt,engine='h5netcdf');print(d,x.time.values,np.nanmean(A[i]))
    x2=x.sel(latitude=slice(64.35,65.65),longitude=slice(23.35,24.65)).load();print(np.nanmean(x2.analysed_sst.values))
    x2.to_netcdf(fl[i]);x.close();os.remove(tt)