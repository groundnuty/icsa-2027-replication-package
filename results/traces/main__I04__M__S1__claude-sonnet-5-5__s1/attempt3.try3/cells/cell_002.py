import xarray as xr
p='/data/icsa2027_data_20261101T090944Z/s1z/'
d=xr.open_dataset(p+'sst_20200601.nc',engine='h5netcdf');print(d)
import os
fs=sorted(os.listdir(p));print(len(fs))
import datetime as dt
s=set(fs);miss=[]
x=dt.date(1991,12,27)
while x<=dt.date(2003,1,5):
    if f"sst_{x:%Y%m%d}.nc" not in s: miss.append(x)
    x+=dt.timedelta(1)
print(miss)