import xarray as xr,re
fl=fs.find(p)
print(len(fl),fl[-1])
ds=xr.open_dataset(fs.open(fl[0],'rb'),engine='h5netcdf')
print(ds)
names=set(f.split('/')[-1] for f in fl)
print([f for f in names if not re.match(r'sst_\d{8}\.nc$',f)])