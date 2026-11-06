import xarray as xr
p='/data/icsa2027_data_20261101T090944Z/s1z/'
d=xr.open_dataset(p+'sst_20090601.nc',engine='h5netcdf');print(d)
fs=set(os.listdir(p))
import pandas as pd
miss=[x for x in pd.date_range('1991-12-27','2003-01-05') if f"sst_{x:%Y%m%d}.nc" not in fs]
miss2=[x for x in pd.date_range('2009-06-01','2009-08-31') if f"sst_{x:%Y%m%d}.nc" not in fs]
print(miss,miss2)