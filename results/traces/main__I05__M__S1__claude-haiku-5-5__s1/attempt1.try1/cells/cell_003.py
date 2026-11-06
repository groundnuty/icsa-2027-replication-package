import pandas as pd
lat=ds.latitude.values; lon=ds.longitude.values
li=np.where((lat>=54.39-1e-6)&(lat<=55.59+1e-6))[0]; lj=np.where((lon>=18.25-1e-6)&(lon<=19.45+1e-6))[0]
print(len(li),len(lj), lat[li[0]],lat[li[-1]],lon[lj[0]],lon[lj[-1]])
# date list
bdates=pd.date_range('1991-12-27','2003-01-05')
tdates=pd.date_range('2021-06-01','2021-08-31')
alld=bdates.append(tdates)
missing=[x for x in alld if not os.path.exists(f"{d}/sst_{x:%Y%m%d}.nc")]
print('missing',len(missing),missing[:5])