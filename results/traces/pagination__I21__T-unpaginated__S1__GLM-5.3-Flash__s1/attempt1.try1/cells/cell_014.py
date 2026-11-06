import fsspec, h5py, numpy as np, datetime as dt, time, pickle
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
EPOCH = np.datetime64('1981-01-01', 's')

def read_region(day):
    last = None
    for attempt in range(4):
        try:
            with fs.open(f'{base}/sst_{day.strftime("%Y%m%d")}.nc', 'rb') as f:
                with h5py.File(f, 'r') as hf:
                    v = hf['analysed_sst']
                    assert v.shape == (1, 626, 1051), v.shape
                    tsec = hf['time'][0]
                    sub = v[0, 192:252, 2:62].astype(np.float32)
            td = EPOCH + np.timedelta64(int(tsec), 's')
            assert td == np.datetime64(day, 's'), (day, td)
            return sub
        except Exception as e:
            last = e
            time.sleep(1.5)
    raise last

d0 = dt.date(1991,12,27)
alld = [d0 + dt.timedelta(days=i) for i in range(4028)]
t0 = time.time()
CH = 1000
for CI in [3]:
    days = alld[CH*CI:CH*(CI+1)]
    with ThreadPoolExecutor(16) as ex:
        arr = np.stack(list(ex.map(read_region, days)))
    np.save(f'/tmp/region_chunk{CI}.npy', arr)
    meta = {'start': days[0].isoformat(), 'end': days[-1].isoformat(), 'n': len(days),
            'sum': float(np.nansum(arr, dtype=np.float64)), 'finite': int(np.isfinite(arr).sum())}
    with open(f'/tmp/region_meta{CI}.pkl','wb') as f: pickle.dump(meta, f)
    print(f"chunk {CI}: {meta} elapsed {time.time()-t0:.1f}s", flush=True)

# target period region slices
tgt_days = [dt.date(2021,6,1)+dt.timedelta(days=i) for i in range(92)]
t1 = time.time()
with ThreadPoolExecutor(16) as ex:
    tgt = np.stack(list(ex.map(read_region, tgt_days)))
np.save('/tmp/target_region.npy', tgt)
meta = {'start': tgt_days[0].isoformat(), 'end': tgt_days[-1].isoformat(), 'n': len(tgt_days),
        'sum': float(np.nansum(tgt, dtype=np.float64)), 'finite': int(np.isfinite(tgt).sum())}
with open('/tmp/target_meta.pkl','wb') as f: pickle.dump(meta, f)
print("target:", meta, f"elapsed {time.time()-t1:.1f}s")
