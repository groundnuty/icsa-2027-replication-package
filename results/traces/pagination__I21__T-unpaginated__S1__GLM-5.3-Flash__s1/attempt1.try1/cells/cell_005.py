import fsspec, h5py, numpy as np, time
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

def read_plane(day):
    p = f'{base}/sst_{day}.nc'
    try:
        with fs.open(p, 'rb') as f:
            with h5py.File(f, 'r') as hf:
                a = hf['analysed_sst'][0]
                return a
    except Exception as e:
        return e

days = ['1992-01-%02d'%d for d in range(1,21)] + ['1997-06-%02d'%d for d in range(1,21)]
for nw in [8, 16]:
    t0 = time.time()
    with ThreadPoolExecutor(nw) as ex:
        res = list(ex.map(read_plane, days))
    errs = [r for r in res if isinstance(r, Exception)]
    ok = [r for r in res if not isinstance(r, Exception)]
    print(f"workers={nw}: {len(days)} planes in {time.time()-t0:.2f}s, errors={len(errs)}, shapes={set(r.shape for r in ok)}, dtypes={set(r.dtype for r in ok)}")
