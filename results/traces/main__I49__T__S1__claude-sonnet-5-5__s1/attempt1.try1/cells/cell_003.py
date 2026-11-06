import fsspec,xarray as xr,numpy as np,re
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
fl=fs.ls(p,detail=False)
print(len(fl),fl[-1],[f for f in fl if not re.search(r'sst_\d{8}\.nc$',f)])
ds=xr.open_dataset(fs.open(fl[0],'rb'),engine='h5netcdf');print(ds)
d=sorted(re.findall(r'sst_(\d{8})',' '.join(fl)));print(d[0],d[-1])