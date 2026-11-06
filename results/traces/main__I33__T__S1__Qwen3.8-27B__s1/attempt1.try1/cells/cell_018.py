
import os, fsspec, datetime, time
import numpy as np
import xarray as xr
from concurrent.futures import ThreadPoolExecutor

fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/ext', exist_ok=True)

def req_dates():
    d0, d1 = datetime.date(1991,12,27), datetime.date(2003,1,5)
    while d0 <= d1:
        yield d0; d0 += datetime.timedelta(days=1)
    d0 = datetime.date(2014,6,1)
    d0e = datetime.date(2014,8,31)
    while d0 <= d0e:
        yield d0; d0 += datetime.timedelta(days=1)
all_dates = list(req_dates())
idx_of = {d:i for i,d in enumerate(all_dates)}
print("n dates:", len(all_dates))

def extract(d):
    i = idx_of[d]
    dest = f'/work/ext/{d.strftime("%Y%m%d")}.npy'
    if os.path.exists(dest):
        return (d, 'cached', None)
    try:
        with fs.open(f'{base}/sst_{d.strftime("%Y%m%d")}.nc','rb') as f:
            ds = xr.open_dataset(f, engine='h5netcdf')
            t = ds['time'].values[0]
            dt = np.datetime64(t).astype(datetime.datetime)
            got = datetime.date(dt.year, dt.month, dt.day)
            if got != d:
                return (d, 'baddate', f'expected {d} got {got}')
            a = np.asarray(ds['analysed_sst'].values[0, 278:338, 613:673], dtype=np.float64)
        tmp = dest + '.tmp'
        np.save(tmp, a)
        os.replace(tmp, dest)
        return (d, 'ok', None)
    except Exception as e:
        return (d, 'err', str(e)[:150])

t0 = time.time()
errs = []; no = nc = 0
for i in range(0, len(all_dates), 300):
    batch = all_dates[i:i+300]
    with ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(extract, batch):
            if r[1]=='ok': no += 1
            elif r[1]=='cached': nc += 1
            else: errs.append(r)
print("ok:", no, "cached:", nc, "errors:", len(errs), "elapsed:", round(time.time()-t0,1), "s")
for e in errs[:15]: print(e)
