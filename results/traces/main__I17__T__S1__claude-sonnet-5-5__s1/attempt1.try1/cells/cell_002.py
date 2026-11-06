import xarray as xr,numpy as np
fl=fs.find(p);print(len(fl),fl[-1])
names=[f.split('/')[-1] for f in fl]
print([n for n in names if not n.startswith('sst_')])
d=xr.open_dataset(fs.open(p+'/sst_20100601.nc','rb'),engine='h5netcdf');print(d)
import collections
dates=sorted(n[4:12] for n in names if n.startswith('sst_'))
# missing in 1991-12-27..2010-08-31
import pandas as pd
rng=pd.date_range('1991-12-27','2010-08-31').strftime('%Y%m%d')
print([x for x in rng if x not in set(dates)][:50])