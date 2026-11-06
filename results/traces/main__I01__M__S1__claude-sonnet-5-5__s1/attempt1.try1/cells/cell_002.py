import xarray as xr
p='/data/icsa2027_data_20261101T090944Z/s1z/sst_20080601.nc'
d=xr.open_dataset(p,engine='h5netcdf');print(d)
import glob
fs=sorted(glob.glob('/data/icsa2027_data_20261101T090944Z/s1z/*.nc'))
import pandas as pd
ds=[f[-11:-3] for f in fs]
need=pd.date_range('1991-12-27','2003-01-05').strftime('%Y%m%d')
print(len(set(need)-set(ds)), sorted(set(need)-set(ds))[:20])
print(len(set(pd.date_range('2008-06-01','2008-08-31').strftime('%Y%m%d'))-set(ds)))