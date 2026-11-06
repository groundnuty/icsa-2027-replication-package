import fsspec, h5py, numpy as np, datetime as dt, time, pickle
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

d0, d1 = dt.date(1991,12,27), dt.date(2003,1,5)
alld = [d0 + dt.timedelta(days=i) for i in range((d1-d0).days+1)]
print("baseline pool days:", len(alld), alld[0], alld[-1])

def read_plane(day):
    last = None
    for attempt in range(4):
        try:
            with fs.open(f'{base}/sst_{day.strftime("%Y%m%d")}.nc','rb') as f:
                with h5py.File(f,'r') as hf:
                    return hf['analysed_sst'][0].astype(np.float32)
        except Exception as e:
            last = e
            time.sleep(1.0)
    raise last

chunk_size = 1000
t0 = time.time()
for ci, cs in enumerate(range(0, len(alld), chunk_size)):
    days = alld[cs:cs+chunk_size]
    with ThreadPoolExecutor(16) as ex:
        arr = np.stack(list(ex.map(read_plane, days)))
    np.save(f'/tmp/baseline_chunk{ci}.npy', arr)
    with open(f'/tmp/baseline_meta{ci}.pkl','wb') as f:
        pickle.dump({'start': days[0].isoformat(), 'n': len(days), 'sum': float(np.nansum(arr, dtype=np.float64)),
                     'finite': int(np.isfinite(arr).sum()), 'shape': arr.shape}, f)
    print(f"chunk {ci}: {days[0]}..{days[-1]} ({len(days)} days) {time.time()-t0:.0f}s "
          f"shape={arr.shape} sum={float(np.nansum(arr,dtype=np.float64)):.6e} finite={int(np.isfinite(arr).sum())}", flush=True)
