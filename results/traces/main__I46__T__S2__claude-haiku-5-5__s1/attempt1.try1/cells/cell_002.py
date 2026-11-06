
v=ds.analysed_sst
print(v.attrs, v.encoding)
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=64.39-1e-6)&(lat<=65.59+1e-6))[0] if 'np' in dir() else None
import numpy as np
la=np.where((lat>=64.39-1e-6)&(lat<=65.59+1e-6))[0]; lo=np.where((lon>=23.41-1e-6)&(lon<=24.61+1e-6))[0]
print(len(la),len(lo),lat[la[[0,-1]]],lon[lo[[0,-1]]])
