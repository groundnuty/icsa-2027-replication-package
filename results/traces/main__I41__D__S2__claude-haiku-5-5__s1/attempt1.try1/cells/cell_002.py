
print(os.path.getsize('/work/sst_s2.nc')/1e9)
v=ds.analysed_sst
print(v.attrs); print(v.encoding)
import numpy as np
lat=ds.latitude.values; lon=ds.longitude.values
print(lat[(lat>=61.5)&(lat<=62.8)].min(), lat[(lat>=61.5)&(lat<=62.8)].max(), ((lat>=61.57-1e-6)&(lat<=62.77+1e-6)).sum())
print(lon[(lon>=20.1)&(lon<=21.4)].min(), lon[(lon>=20.1)&(lon<=21.4)].max(), ((lon>=20.17-1e-6)&(lon<=21.37+1e-6)).sum())
