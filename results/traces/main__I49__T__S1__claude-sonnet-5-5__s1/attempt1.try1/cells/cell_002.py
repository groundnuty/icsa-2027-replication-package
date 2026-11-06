import xarray as xr,numpy as np,re
fl=fs.ls(p,detail=False)
print(len(fl),fl[-1],[f for f in fl if not re.search(r'sst_\d{8}\.nc$',f)])
ds=xr.open_dataset(fs.open(fl[0],'rb'),engine='h5netcdf');print(ds)