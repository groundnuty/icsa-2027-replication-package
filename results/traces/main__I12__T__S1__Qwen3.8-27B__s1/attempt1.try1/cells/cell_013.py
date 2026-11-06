import fsspec, xarray as xr, numpy as np, time, os, datetime as dt
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
lat_idx = np.load('data/lat_idx.npy'); lon_idx = np.load('data/lon_idx.npy')

def fetch(datestr):
    out = f'data/crop_{datestr}.npy'
    if os.path.exists(out):
        return datestr, 'skip'
    try:
        f = fs.open(f'{base}/sst_{datestr}.nc', 'rb')
        ds = xr.open_dataset(f, engine='h5netcdf')
        v = ds['analysed_sst']
        tval = str(ds['time'].values[0])[:10]
        if tval != f'{datestr[:4]}-{datestr[4:6]}-{datestr[6:]}':
            ds.close(); f.close(); return datestr, f'TIME_MISMATCH {tval}'
        arr = v.values[0][lat_idx, :][:, lon_idx].astype('float64')
        ds.close(); f.close()
        np.save(out, arr)
        return datestr, 'ok'
    except Exception as e:
        return datestr, f'ERR {type(e).__name__} {str(e)[:80]}'

def daterange(a, b):
    d = a
    while d <= b:
        yield d.strftime('%Y%m%d'); d += dt.timedelta(days=1)

dates = list(daterange(dt.date(1991,12,27), dt.date(2003,1,5))) + list(daterange(dt.date(2009,6,1), dt.date(2009,8,31)))
batch = dates[3600:4120]
t0 = time.time()
with ThreadPoolExecutor(max_workers=8) as ex:
    results = list(ex.map(fetch, batch))
print('elapsed %.1f s' % (time.time()-t0), Counter(r[1] for r in results))

# verify all 4120 present
missing = [d for d in dates if not os.path.exists(f'data/crop_{d}.npy')]
print('missing:', missing[:20], 'count', len(missing))