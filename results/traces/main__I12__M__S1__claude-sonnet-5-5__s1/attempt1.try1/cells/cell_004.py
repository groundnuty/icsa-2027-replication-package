import os,numpy as np,pandas as pd,xarray as xr
p='/data/icsa2027_data_20261101T090944Z/s1z/'
fs=set(os.listdir(p))
miss=[x for x in pd.date_range('1991-12-27','2003-01-05') if f"sst_{x:%Y%m%d}.nc" not in fs]
miss2=[x for x in pd.date_range('2009-06-01','2009-08-31') if f"sst_{x:%Y%m%d}.nc" not in fs]
print(miss,miss2)
d=xr.open_dataset(p+'sst_20090601.nc',engine='h5netcdf')
lat=d.latitude.values;lon=d.longitude.values
ii=np.where((lat>=56.09-1e-4)&(lat<=57.29+1e-4))[0];jj=np.where((lon>=10.55-1e-4)&(lon<=11.75+1e-4))[0]
print(lat[ii][[0,-1]],lon[jj][[0,-1]],len(ii),len(jj),d.analysed_sst.attrs)