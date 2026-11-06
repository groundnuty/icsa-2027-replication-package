import xarray as xr, numpy as np, os, pandas as pd
d='/data/icsa2027_data_20261101T090944Z/s1z'
ds=xr.open_dataset(f'{d}/sst_19820101.nc', engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
li=np.where((lat>=54.39-1e-6)&(lat<=55.59+1e-6))[0]; lj=np.where((lon>=18.25-1e-6)&(lon<=19.45+1e-6))[0]
print(len(li),len(lj), lat[li[0]],lat[li[-1]],lon[lj[0]],lon[lj[-1]])
bdates=pd.date_range('1991-12-27','2003-01-05')
tdates=pd.date_range('2021-06-01','2021-08-31')
alld=bdates.append(tdates)
missing=[x for x in alld if not os.path.exists(f"{d}/sst_{x:%Y%m%d}.nc")]
print('missing',len(missing),missing[:5])