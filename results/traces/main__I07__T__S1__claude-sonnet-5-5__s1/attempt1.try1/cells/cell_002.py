import xarray as xr,re,numpy as np
fl=sorted(fs.find(p));print(len(fl),fl[0],fl[-1])
ds=[re.search(r'(\d{8})',f).group(1) for f in fl]
import pandas as pd
d=pd.to_datetime(ds,format='%Y%m%d');print(d.is_unique)
full=pd.date_range(d.min(),d.max());print(len(full),full.difference(d)[:50])
x=xr.open_dataset(fs.open(fl[0],'rb'),engine='h5netcdf');print(x)