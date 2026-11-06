fl=fs.ls(p,detail=False)
print(len(fl),fl[-1])
import xarray as xr,os
os.makedirs('/work',exist_ok=True)
fs.get(fl[0],'/work/a.nc')
d=xr.open_dataset('/work/a.nc',engine='h5netcdf');print(d)
names=set(os.path.basename(f) for f in fl)