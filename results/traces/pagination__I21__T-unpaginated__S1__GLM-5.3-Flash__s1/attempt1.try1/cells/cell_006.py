import fsspec, h5py, numpy as np, time, traceback
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

def read_plane(day):
    try:
        with fs.open(f'{base}/sst_{day}.nc', 'rb') as f:
            with h5py.File(f, 'r') as hf:
                return hf['analysed_sst'][0]
    except Exception as e:
        return (day, repr(e))

with ThreadPoolExecutor(4) as ex:
    res = list(ex.map(read_plane, ['1992-01-01','1992-01-02','1992-01-03','1992-01-04']))
for r in res[:2]:
    print(r if isinstance(r, tuple) else "OK", )
    if isinstance(r, tuple):
        print(r[1][:500])
