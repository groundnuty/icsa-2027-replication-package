import fsspec, h5py, numpy as np, time, datetime as dt, json, concurrent.futures as cf
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
i0,i1,j0,j1 = 66,125,531,590

names = set(fs.ls(base))
span_start, span_end = dt.date(1991,12,27), dt.date(2003,1,5)
span_dates = [span_start + dt.timedelta(days=i) for i in range((span_end-span_start).days+1)]
tgt_start, tgt_end = dt.date(2022,6,1), dt.date(2022,8,31)
tgt_dates = [tgt_start + dt.timedelta(days=i) for i in range((tgt_end-tgt_start).days+1)]
need = [f'sst_{d.strftime("%Y%m%d")}.nc' for d in span_dates+tgt_dates]
missing = [n for n in need if f'{base}/{n}' not in names]
print('span days:', len(span_dates), 'target days:', len(tgt_dates), 'missing files:', len(missing))

with fs.open(f'{base}/sst_19920601.nc','rb') as f:
    with h5py.File(f,'r') as h:
        lat_ref = h['latitude'][:].copy(); lon_ref = h['longitude'][:].copy()
        print('time attrs:', {k: v for k,v in h['time'].attrs.items()})

def read_one(dstr):
    err = None
    for attempt in range(5):
        try:
            with fs.open(f'{base}/sst_{dstr}.nc','rb') as f:
                with h5py.File(f,'r') as h:
                    lat = h['latitude'][:]; lon = h['longitude'][:]
                    if not (np.array_equal(lat, lat_ref) and np.array_equal(lon, lon_ref)):
                        raise ValueError(f'grid mismatch {dstr}')
                    return dstr, h['analysed_sst'][0, i0:i1+1, j0:j1+1].astype(np.float64)
        except Exception as e:
            err = e; time.sleep(0.5*(attempt+1))
    print('FAILED', dstr, repr(err))
    return dstr, None

keys = [d.strftime('%Y%m%d') for d in span_dates]
t0 = time.time(); data = {}; failed = []
with cf.ThreadPoolExecutor(96) as ex:
    for dstr, arr in ex.map(read_one, keys):
        if arr is None: failed.append(dstr)
        else: data[dstr] = arr
for dstr in list(failed):
    d2, arr = read_one(dstr)
    if arr is not None: data[d2] = arr; failed.remove(d2)
print(f'read {len(data)}/{len(keys)} in {time.time()-t0:.1f}s; failed: {len(failed)}')
assert not failed, failed[:5]
stack = np.stack([data[d.strftime('%Y%m%d')] for d in span_dates])
np.save('/tmp/base_span.npy', stack)
with open('/tmp/meta.json','w') as f:
    json.dump({'span':[d.isoformat() for d in span_dates], 'tgt':[d.isoformat() for d in tgt_dates], 'idx':[int(i0),int(i1),int(j0),int(j1)]}, f)
print('stack', stack.shape, stack.dtype, 'finite frac', round(float(np.isfinite(stack).mean()),4))

import xarray as xr, random
random.seed(0)
for dstr in random.sample(keys, 3):
    with fs.open(f'{base}/sst_{dstr}.nc','rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        print('file', dstr, '-> time', ds.time.values[0])
        ds.close()
