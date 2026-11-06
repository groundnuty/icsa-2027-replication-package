import fsspec, h5py, numpy as np, json, datetime as dt, time, concurrent.futures as cf
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
meta = json.load(open('/tmp/meta.json'))
i0,i1,j0,j1 = meta['idx']
tgt = [dt.date.fromisoformat(s) for s in meta['tgt']]
lat_ref = lon_ref = None

def read_one(dstr):
    for attempt in range(5):
        try:
            with fs.open(f'{base}/sst_{dstr}.nc','rb') as f:
                with h5py.File(f,'r') as h:
                    lat = h['latitude'][:]; lon = h['longitude'][:]
                    return dstr, h['analysed_sst'][0, i0:i1+1, j0:j1+1].astype(np.float64), lat, lon
        except Exception:
            if attempt==4: raise
            time.sleep(0.5*(attempt+1))

keys = [d.strftime('%Y%m%d') for d in tgt]
t0=time.time(); data={}; refs={}
with cf.ThreadPoolExecutor(48) as ex:
    for dstr, arr, lat, lon in ex.map(read_one, keys):
        data[dstr]=arr; refs[dstr]=(lat.tobytes(), lon.tobytes())
assert len(data)==92 and len(set(refs.values()))==1, 'read/grid problem'
print(f'target read {len(data)} files in {time.time()-t0:.1f}s')
tgt_stack = np.stack([data[d.strftime('%Y%m%d')] for d in tgt])
np.save('/tmp/tgt_stack.npy', tgt_stack)
print('target stack', tgt_stack.shape, 'finite frac', round(float(np.isfinite(tgt_stack).mean()),4))
# sea cells: finite on EVERY target day
sea = np.isfinite(tgt_stack).all(axis=0)
print('sea cells:', int(sea.sum()), 'of', sea.size)
np.save('/tmp/sea.npy', sea)
per_day_finite = np.isfinite(tgt_stack).sum(axis=(1,2))
print('finite per day: min', per_day_finite.min(), 'max', per_day_finite.max())
