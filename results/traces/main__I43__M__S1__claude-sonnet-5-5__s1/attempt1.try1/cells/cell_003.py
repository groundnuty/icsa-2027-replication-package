import os,numpy as np,pandas as pd,xarray as xr
D='/data/icsa2027_data_20261101T090944Z/s1z/'
fs=set(os.listdir(D))
need=pd.date_range('1991-12-27','2003-01-05').tolist()+list(pd.date_range('2017-06-01','2017-08-31'))
miss=[d for d in need if f"sst_{d:%Y%m%d}.nc" not in fs];print(len(miss),miss[:10])
d=xr.open_dataset(D+'sst_20170601.nc',engine='h5netcdf')
la=d.latitude.values;lo=d.longitude.values
li=np.where((la>=62.25-1e-4)&(la<=63.45+1e-4))[0];oi=np.where((lo>=18.73-1e-4)&(lo<=19.93+1e-4))[0]
print(la[li[[0,-1]]],lo[oi[[0,-1]]],len(li),len(oi))