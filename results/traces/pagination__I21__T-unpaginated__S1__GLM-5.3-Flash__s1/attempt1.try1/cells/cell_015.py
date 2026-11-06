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

days = [dt.date(2002,12,9)+dt.timedelta(days=i) for i in range(29)]
print("tail days:", days[0], "..", days[-1], "n=", len(days))
t0 = time.time()
with ThreadPoolExecutor(16) as ex:
    arr = np.stack(list(ex.map(read_region, days)))
np.save('/tmp/region_chunk4.npy', arr)
meta = {'start': days[0].isoformat(), 'end': days[-1].isoformat(), 'n': len(days),
        'sum': float(np.nansum(arr, dtype=np.float64)), 'finite': int(np.isfinite(arr).sum())}
with open('/tmp/region_meta4.pkl','wb') as f: pickle.dump(meta, f)
print(f"tail: {meta} elapsed {time.time()-t0:.1f}s")
print("all baseline days:", 4*1000+29)
