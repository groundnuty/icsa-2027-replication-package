import xarray as xr,numpy as np,pandas as pd,glob,json,os
fl=sorted(glob.glob('/work/c/*.nc'))
X=xr.concat([xr.open_dataset(f) for f in fl],dim='time').load()
print(X.analysed_sst.shape,X.latitude.values[[0,-1]],X.longitude.values[[0,-1]])
t=pd.DatetimeIndex(X.time.values);exp=pd.to_datetime([f[-11:-3] for f in fl])
print((t==exp).all(), float(X.analysed_sst.min()),float(X.analysed_sst.max()), X.analysed_sst.dtype)
lat=X.latitude.values;lon=X.longitude.values
li=np.where((lat>=64.39-1e-4)&(lat<=65.59+1e-4))[0];lj=np.where((lon>=23.41-1e-4)&(lon<=24.61+1e-4))[0]
print(lat[li][[0,-1]],lon[lj][[0,-1]],len(li),len(lj))
np.save('/work/sst.npy',X.analysed_sst.values[:,li[0]:li[-1]+1,lj[0]:lj[-1]+1].astype('float64'))
np.save('/work/t.npy',t.values);np.save('/work/lat.npy',lat[li]);np.save('/work/lon.npy',lon[lj])