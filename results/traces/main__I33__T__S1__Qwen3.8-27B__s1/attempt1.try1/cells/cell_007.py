
import os, fsspec, datetime, time
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/tmp/mhw', exist_ok=True)

def req_dates():
    d0, d1 = datetime.date(1991,12,27), datetime.date(2003,1,5)
    while d0 <= d1:
        yield d0; d0 += datetime.timedelta(days=1)
    d0 = datetime.date(2014,6,1)
    d0e = datetime.date(2014,8,31)
    while d0 <= d0e:
        yield d0; d0 += datetime.timedelta(days=1)

all_req = list(req_dates())
print("total required:", len(all_req))

def fetch(d):
    name = f'sst_{d.strftime("%Y%m%d")}.nc'
    dest = f'/tmp/mhw/{name}'
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return (name, 'cached', None)
    src = f'{base}/{name}'
    try:
        with fs.open(src, 'rb') as f, open(dest, 'wb') as out:
            out.write(f.read())
        return (name, 'ok', None)
    except Exception as e:
        return (name, 'err', str(e)[:120])

# test batch of 200 first
t0 = time.time()
batch = all_req[:200]
results = []
with ThreadPoolExecutor(max_workers=8) as ex:
    for r in ex.map(fetch, batch):
        results.append(r)
dt = time.time() - t0
errs = [r for r in results if r[1]=='err']
cok = sum(1 for r in results if r[1]=='ok')
print(f"batch1: {len(results)} files in {dt:.1f}s ({dt/len(results)*1000:.0f} ms/file), ok={cok}, err={len(errs)}")
for e in errs[:10]: print(e)
