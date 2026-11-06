import numpy as np, h5py, sys
print("numpy", np.__version__)
print("h5py", h5py.__version__)
import xarray
print("xarray", xarray.__version__)
import scipy
print("scipy", scipy.__version__)
f = h5py.File('/work/sst_s2.nc','r')
d = f['analysed_sst']
print("chunks:", d.chunks, "compression:", d.compression, "shuffle:", getattr(d,'shuffle',None))
print("lat chunks:", f['latitude'].chunks, "lon chunks:", f['longitude'].chunks)
tv = f['time'][:]
print("time dtype", tv.dtype, tv[:3], tv[-3:])
