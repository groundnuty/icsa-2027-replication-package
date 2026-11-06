import numpy as np,pandas as pd,xarray as xr,glob
days=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2021-06-01','2021-08-31'))
arr=[];
for t in days:
    x=xr.open_dataset(f'/work/raw/{t:%Y%m%d}.nc',engine='h5netcdf')
    if not arr:
        lat=x.latitude.values;lon=x.longitude.values
        li=np.where((lat>=61.57-1e-4)&(lat<=62.77+1e-4))[0];lo=np.where((lon>=20.17-1e-4)&(lon<=21.37+1e-4))[0]
        print(lat[li],lon[lo],x.analysed_sst.dtype,x.analysed_sst.attrs)
    assert x.time.size==1
    arr.append(x.analysed_sst.values[0][np.ix_(li,lo)].astype('float64'))
    x.close()
A=np.array(arr);np.save('/work/A.npy',A);np.save('/work/ll.npy',np.array([lat[li],lon[lo]],dtype=object),allow_pickle=True)
print(A.shape,np.nanmin(A),np.nanmax(A),np.isnan(A).mean())