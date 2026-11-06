import numpy as np, xarray as xr
from datetime import date, timedelta
PATH = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(PATH, engine="h5netcdf")
tv = ds.time.values
datestr = '1991-12-27'
i = int(np.searchsorted(tv, np.datetime64(datestr)))
print("i", i, tv[i], repr(tv[i].astype('datetime64[D]')), str(tv[i].astype('datetime64[D]')))
print(tv[i] == np.datetime64(datestr))
# which date fails?
for k in range(-5, 6):
    t = date(1992,1,1) + timedelta(days=k)
    s = f"{t.year:04d}-{t.month:02d}-{t.day:02d}"
    j = int(np.searchsorted(tv, np.datetime64(s)))
    ok = str(tv[j].astype('datetime64[D]')) == s
    print(s, j, str(tv[j]), ok)
ds.close()
