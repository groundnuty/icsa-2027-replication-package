import shutil, os, time, fsspec
total, used, free = shutil.disk_usage('/work')
print(f'disk /work: total={total/1e9:.1f}GB free={free/1e9:.1f}GB')
import numpy as np
print('numpy', np.__version__, 'xarray', __import__('xarray').__version__)
fs = fsspec.filesystem('onedata')
# timing test: 10 sequential downloads
t0 = time.time()
for d in ['20210602','20210603','20210604','20210605','20210606','19920601','19920602','20030105','19911227','19980228']:
    src = f'icsa2027_data_20261101T090944Z/s1z/sst_{d}.nc'
    dst = f'/work/data/sst_{d}.nc'
    if not os.path.exists(dst):
        fs.get(src, dst)
dt = time.time()-t0
print(f'10 files in {dt:.1f}s -> {10/dt:.1f} files/s')
