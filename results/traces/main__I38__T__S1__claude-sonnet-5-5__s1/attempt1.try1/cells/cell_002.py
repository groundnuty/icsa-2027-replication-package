fl=sorted(fs.ls(p,detail=False));print(len(fl),fl[-1])
import xarray as xr
ds=xr.open_dataset(fs.open(fl[0],'rb'),engine='h5netcdf');print(ds)
names=[f.split('_')[-1][:8] for f in fl]
import collections
print(collections.Counter(n[:4] for n in names))
print([f for f in fl if not f.endswith('.nc')][:5])