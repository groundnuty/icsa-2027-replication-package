import numpy as np
lat=np.load('/work/lat.npy');lon=np.load('/work/lon.npy');print(lat[[0,-1]],lon[[0,-1]],len(lat),len(lon))
a=np.load('/work/d/20190601.npy');print(a.shape,np.nanmean(a),np.isnan(a).sum())