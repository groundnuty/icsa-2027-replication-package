import xarray as xr
fl=fs.ls(p);print(len(fl),fl[-1])
import re
names=sorted(f for f in fl if f.endswith('.nc'));print(len(names))
ds=xr.open_dataset(fs.open(names[0],'rb'),engine='h5netcdf');print(ds)
ds2=xr.open_dataset(fs.open('%s/sst_19920101.nc'%p,'rb'),engine='h5netcdf');print(ds2.analysed_sst.encoding if 'analysed_sst' in ds2 else '')