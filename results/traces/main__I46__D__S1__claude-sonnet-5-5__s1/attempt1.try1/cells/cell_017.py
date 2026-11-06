import xarray as xr,pandas as pd,numpy as np,glob
fl=sorted(glob.glob('/work/c/*.nc'))
A=[];T=[]
for f in fl:
    x=xr.open_dataset(f,engine='h5netcdf')
    A.append(x.analysed_sst.values[0]);T.append(x.time.values[0]);lat=x.latitude.values;lon=x.longitude.values;x.close()
A=np.array(A);t=pd.DatetimeIndex(T)
print((t==pd.to_datetime([f[-11:-3] for f in fl])).all())
li=np.where((lat>=64.39-1e-4)&(lat<=65.59+1e-4))[0];lj=np.where((lon>=23.41-1e-4)&(lon<=24.61+1e-4))[0]
S=A[:,li[0]:li[-1]+1,lj[0]:lj[-1]+1].astype('float64')
np.save('/work/sst.npy',S);np.save('/work/t.npy',t.values);np.save('/work/lat.npy',lat[li]);np.save('/work/lon.npy',lon[lj])
fin=np.isfinite(S);print(S.shape,fin.all(axis=(1,2)).sum(), np.unique(fin.sum(axis=(1,2)))[:10])
# anomaly check: daily regional mean
m=np.nanmean(S,axis=(1,2));print(np.abs(np.diff(m)).max())
print(lat[li][:3],lon[lj][:3])