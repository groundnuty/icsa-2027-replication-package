
import os, shutil, fsspec, datetime, time
from concurrent.futures import ThreadPoolExecutor
os.makedirs('~', exist_ok=True)
# move existing
moved = 0
for f in os.listdir('/tmp/mhw'):
    s = f'/tmp/mhw/{f}'
    if os.path.getsize(s) > 1000:
        shutil.move(s, f'~/{f}'); moved += 1
    else:
        os.remove(s)
print("moved:", moved)

fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z'

def req_dates():
    d0, d1 = datetime.date(1991,12,27), datetime.date(2003,1,5)
    while d0 <= d1:
        yield d0; d0 += datetime.timedelta(days=1)
    d0 = datetime.date(2014,6,1)
    d0e = datetime.date(2014,8,31)
    while d0 <= d0e:
        yield d0; d0 += datetime.timedelta(days=1)
all_req = list(req_dates())

def fetch(d):
    name = f'sst_{d.strftime("%Y%m%d")}.nc'
    dest = f'~/{name}'
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return (name, 'cached', None)
    src = f'{base}/{name}'
    try:
        with fs.open(src, 'rb') as f, open(dest, 'wb') as out:
            out.write(f.read())
        return (name, 'ok', None)
    except Exception as e:
        return (name, 'err', str(e)[:200])

t0 = time.time()
errs = []; no = nc = 0
for i in range(0, len(all_req), 400):
    batch = all_req[i:i+400]
    with ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(fetch, batch):
            if r[1]=='ok': no += 1
            elif r[1]=='cached': nc += 1
            else: errs.append(r)
print("ok:", no, "cached:", nc, "errors:", len(errs), "elapsed:", round(time.time()-t0,1))
for e in errs[:10]: print(e)
n_ok_files = len([f for f in os.listdir('~') if os.path.getsize(f'~/{f}')>1000])
print("files on disk:", n_ok_files)
