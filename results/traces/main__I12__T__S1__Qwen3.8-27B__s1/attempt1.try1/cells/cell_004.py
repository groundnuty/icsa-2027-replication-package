import fsspec, time
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
# check edge files exist
for d in ['19911227','19911231','19920101','20021231','20030101','20030105','20090601','20090831']:
    p = f'{base}/sst_{d}.nc'
    try:
        meta = fs.info(p)
        print(d, meta.get('size'))
    except Exception as e:
        print(d, 'MISSING', type(e).__name__, str(e)[:100])