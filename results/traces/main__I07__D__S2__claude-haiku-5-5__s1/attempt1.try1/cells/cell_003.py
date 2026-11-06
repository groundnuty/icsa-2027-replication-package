
import fsspec, xarray, os, numpy as np, pandas as pd
print(os.path.exists('/work/sst_s2.nc'), os.path.getsize('/work/sst_s2.nc') if os.path.exists('/work/sst_s2.nc') else None)
ds = xarray.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
ilat=np.where((lat>=54.45-1e-6)&(lat<=55.65+1e-6))[0]; ilon=np.where((lon>=16.05-1e-6)&(lon<=17.25+1e-6))[0]
print(len(ilat),len(ilon), lat[ilat[[0,-1]]], lon[ilon[[0,-1]]])
t=ds.time.values
m=((t>=np.datetime64('1991-12-27'))&(t<=np.datetime64('2003-01-05')))|((t>=np.datetime64('2021-06-01'))&(t<=np.datetime64('2021-08-31')))
tidx=np.where(m)[0]; print(len(tidx), pd.Timestamp(t[tidx[0]]), pd.Timestamp(t[tidx[-1]]))
sub=ds.analysed_sst.isel(time=tidx, latitude=ilat, longitude=ilon).load()
print(sub.shape, np.isnan(sub.values).sum(), np.nanmin(sub.values), np.nanmax(sub.values))
