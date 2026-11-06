import xarray as xr, numpy as np, os, datetime as dt
d='/data/icsa2027_data_20261101T090944Z/s1z'
names=set(os.listdir(d))
ds=xr.open_dataset(f'{d}/sst_19820101.nc',engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
ii=np.where((lat>=54.17-1e-6)&(lat<=55.37+1e-6))[0]; jj=np.where((lon>=13.25-1e-6)&(lon<=14.45+1e-6))[0]
print(len(ii),len(jj), lat[ii[0]],lat[ii[-1]],lon[jj[0]],lon[jj[-1]])
req=[]
t=dt.date(1991,12,27)
while t<=dt.date(2003,1,5): req.append(t); t+=dt.timedelta(1)
t=dt.date(2014,5,27)
while t<=dt.date(2014,8,31): req.append(t); t+=dt.timedelta(1)
missing=[r for r in req if f"sst_{r:%Y%m%d}.nc" not in names]
print(len(req), missing[:10], len(missing))
a=ds.analysed_sst.values[0,ii[0]:ii[-1]+1, jj[0]:jj[-1]+1]
print(a.shape, np.isnan(a).mean(), ds.analysed_sst.encoding.get('scale_factor'), ds.analysed_sst.encoding.get('dtype'))