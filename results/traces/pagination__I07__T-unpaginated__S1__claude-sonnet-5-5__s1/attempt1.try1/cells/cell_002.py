import re,xarray as xr
fl=sorted(fs.find(p))
print(len(fl),fl[0],fl[-1])
ds=[re.search(r'(\d{8})',f).group(1) for f in fl]
print([f for f in fl if not re.search(r'sst_\d{8}\.nc$',f)])
import pandas as pd
alld=pd.to_datetime(ds,format='%Y%m%d')
full=pd.date_range(alld[0],alld[-1]);print(len(full),len(alld),full.difference(alld)[:20])
d=xr.open_dataset(fs.open(fl[0],'rb'),engine='h5netcdf');print(d)