import fsspec, h5py, numpy as np, time
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

def read_plane(day):
    try:
        with fs.open(f'{base}/sst_{day.strftime("%Y%m%d")}.nc', 'rb') as f:
            with h5py.File(f, 'r') as hf:
                return hf['analysed_sst'][0]
    except Exception as e:
        return e

import datetime as dt
days = [dt.date(1992,1,1)+dt.timedelta(days=i) for i in range(60)]
for nw in [8, 16]:
    t0 = time.time()
    with ThreadPoolExecutor(nw) as ex:
        res = list(ex.map(read_plane, days))
    errs = [r for r in res if isinstance(r, Exception)]
    ok = [r for r in res if not isinstance(r, Exception)]
    el = time.time()-t0
    print(f"workers={nw}: {len(days)} planes in {el:.2f}s ({len(days)/el:.1f}/s), errors={len(errs)}, shapes={set(r.shape for r in ok)}, dtypes={set(r.dtype for r in ok)}")
