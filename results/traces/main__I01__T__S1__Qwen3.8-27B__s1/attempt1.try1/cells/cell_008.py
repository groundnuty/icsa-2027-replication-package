
import fsspec, xarray as xr, numpy as np
from datetime import date, timedelta
fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z/'

f = fs.open(base + 'sst_19920229.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds['time'].values, ds['time'].attrs)
print(ds['analysed_sst'].attrs)
print('missing values attr:', ds.attrs.get('missing values'))
ds.close()

# Build date lists
def daterange(a, b):
    d, out = a, []
    while d <= b:
        out.append(d); d += timedelta(days=1)
    return out

base_dates = daterange(date(1992,1,1), date(2002,12,31))
extra_pre  = daterange(date(1991,12,27), date(1991,12,31))
extra_post = daterange(date(2003,1,1), date(2003,1,5))
target_dates = daterange(date(2008,6,1), date(2008,8,31))
need = sorted(set(extra_pre + base_dates + extra_post + target_dates))
print("need count:", len(need), "from", need[0], "to", need[-1])

import concurrent.futures as cf
missing = []
def check(d):
    p = base + f"sst_{d:%Y%m%d}.nc"
    try:
        fs.info(p)
    except Exception:
        missing.append(d)
with cf.ThreadPoolExecutor(max_workers=16) as ex:
    list(ex.map(check, need))
print("missing:", missing)
