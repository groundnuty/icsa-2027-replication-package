import fsspec, os, time
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/dl', exist_ok=True)

dates = ['20210602','20210603','20210604','20210605','20210606','20210607','20210608','20210609']
def get(d):
    p = f'/work/dl/sst_{d}.nc'
    if not os.path.exists(p):
        fs.get(base + f'/sst_{d}.nc', p)
    return d

t0 = time.time()
with ThreadPoolExecutor(max_workers=8) as ex:
    list(ex.map(get, dates))
dt = time.time() - t0
print(f"8 files in {dt:.2f}s -> {len(dates)/dt:.2f} files/s")
print(sum(os.path.getsize(f'/work/dl/sst_{d}.nc') for d in dates)/8/1024, "KB avg")
