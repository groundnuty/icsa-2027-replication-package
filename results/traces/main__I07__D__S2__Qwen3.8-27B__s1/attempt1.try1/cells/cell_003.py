import xarray as xr, numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print('var attrs:', ds['analysed_sst'].attrs)
print('time attrs:', ds['time'].attrs)
print('lat attrs:', ds['latitude'].attrs)
print('lon attrs:', ds['longitude'].attrs)

lat = ds['latitude'].values  # float32
lon = ds['longitude'].values
print('lat range', lat.min(), lat.max(), 'step', np.diff(lat).min(), np.diff(lat).max())
print('lon range', lon.min(), lon.max(), 'step', np.diff(lon).min(), np.diff(lon).max())

# region cells (inclusive bounds), use exact multiples of 1/50 to avoid float noise
li = np.where((lat >= np.float32(54.45) - 1e-6) & (lat <= np.float32(55.65) + 1e-6))[0]
lo = np.where((lon >= np.float32(16.05) - 1e-6) & (lon <= np.float32(17.25) + 1e-6))[0]
print('lat idx', li.min(), li.max(), 'count', len(li))
print('lon idx', lo.min(), lo.max(), 'count', len(lo))
print('lat values:', lat[li[0]], lat[li[-1]])
print('lon values:', lon[lo[0]], lon[lo[-1]])
# check grid spacing consistency via *50
print('lat*50:', np.round(lat[li]*50).astype(int)[:5], np.round(lat[li]*50).astype(int)[-5:])
print('lon*50:', np.round(lon[lo]*50).astype(int)[:5], np.round(lon[lo]*50).astype(int)[-5:])

t = ds.indexes['time']
import pandas as pd
ti_all = np.arange(len(t))
# completeness check
tdates = pd.DatetimeIndex(t).date
gaps = [ (tdates[i].isoformat(), tdates[i+1].isoformat()) for i in range(len(tdates)-1) if (tdates[i+1]-tdates[i]).days != 1 ]
print('time gaps:', gaps[:5], 'n gaps', len(gaps))
print('first', tdates[0], 'last', tdates[-1])

def tidx(d):
    return np.where(tdates == d)[0]
import datetime as dt
for d in ['1991-12-27','1992-01-01','2002-12-31','2003-01-05','2021-06-01','2021-08-31']:
    print(d, tidx(dt.date.fromisoformat(d)))

# SST value range over region/target to confirm Kelvin
sub = ds['analysed_sst'].isel(time=tidx(dt.date(2021,7,15)), latitude=li, longitude=lo).values
print('sst sample 2021-07-15 region: min', sub.min(), 'max', sub.max(), 'nan frac', np.isnan(sub).mean())
sub2 = ds['analysed_sst'].isel(time=tidx(dt.date(2000,7,15)), latitude=li, longitude=lo).values
print('sst sample 2000-07-15 region: min', sub2.min(), 'max', sub2.max())
print('numpy', np.__version__)
