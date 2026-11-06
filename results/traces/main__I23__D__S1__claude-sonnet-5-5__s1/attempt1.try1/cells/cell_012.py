import xarray as xr,numpy as np,pandas as pd,json,os
z=np.load('/work/data.npz');lat=z['lat'];lon=z['lon']
print(mh.sum() if 'mh' in dir() else 'nomh')