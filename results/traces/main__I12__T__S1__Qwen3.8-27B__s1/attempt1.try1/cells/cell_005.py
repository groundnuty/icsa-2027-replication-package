import fsspec, xarray as xr, numpy as np, time, os
from concurrent.futures import ThreadPoolExecutor, as_completed
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('data', exist_ok=True)

# region selection (from earlier: lats 56.10..57.28, lons 10.56..11.74)
def get_coords():
    f = fs.open(f'{base}/sst_19920601.nc','rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds['latitude'].values.astype('float64')
    lon = ds['longitude'].values.astype('float64')
    ds.close(); f.close()
    return lat, lon

lat, lon = get_coords()
lat_idx = np.where((lat >= 56.09) & (lat <= 57.29))[0]
lon_idx = np.where((lon >= 10.55) & (lon <= 11.75))[0]
print('n lat', len(lat_idx), 'n lon', len(lon_idx))
np.save('data/lat_idx.npy', lat_idx); np.save('data/lon_idx.npy', lon_idx)
np.save('data/lat_values.npy', lat[lat_idx]); np.save('data/lon_values.npy', lon[lon_idx])

def fetch(datestr):
    out = f'data/crop_{datestr}.npy'
    if os.path.exists(out):
        return datestr, 'skip'
    try:
        f = fs.open(f'{base}/sst_{datestr}.nc', 'rb')
        ds = xr.open_dataset(f, engine='h5netcdf')
        v = ds['analysed_sst']
        # verify time coord
        tval = str(ds['time'].values[0])[:10]
        if tval != f'{datestr[:4]}-{datestr[4:6]}-{datestr[6:]}':
            ds.close(); f.close()
            return datestr, f'TIME_MISMATCH {tval}'
        arr = v.values[0][lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].astype('float64')
        # ensure slicing is exactly right
        arr = v.values[0][lat_idx, :][:, lon_idx]
        ds.close(); f.close()
        np.save(out, arr)
        return datestr, 'ok'
    except Exception as e:
        return datestr, f'ERR {type(e).__name__} {str(e)[:80]}'

import datetime as dt
def daterange(a, b):
    d = a
    while d <= b:
        yield d.strftime('%Y%m%d')
        d += dt.timedelta(days=1)

dates = list(daterange(dt.date(1991,12,27), dt.date(2003,1,5))) + list(daterange(dt.date(2009,6,1), dt.date(2009,8,31)))
print('total dates', len(dates))

t0 = time.time()
batch = dates[:100]
with ThreadPoolExecutor(max_workers=8) as ex:
    results = list(ex.map(fetch, batch))
dt_ = time.time() - t0
from collections import Counter
print('elapsed %.1f s for %d files' % (dt_, len(batch)))
print(Counter(r[1] for r in results))