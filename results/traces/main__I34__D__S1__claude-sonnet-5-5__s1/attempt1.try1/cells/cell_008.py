import numpy as np,pandas as pd
lat=np.load('/work/lat.npy');lon=np.load('/work/lon.npy')
print(lat,lon)
a=np.load('/work/d/sst_20070601.nc.npy');print(a.shape,np.nanmin(a),np.nanmax(a),np.isnan(a).sum())