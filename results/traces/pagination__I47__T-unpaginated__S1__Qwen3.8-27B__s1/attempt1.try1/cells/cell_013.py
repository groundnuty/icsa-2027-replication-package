
from datetime import date
exec(open('/dev/null').read())  # noop
import numpy as np, json
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor
import fsspec, xarray as xr, time

BASE = '/icsa2027_data_20261101T090944Z/s1z'
fs = fsspec.filesystem('onedata')
IL, IL2 = 545, 605
IJ, IJ2 = 721, 781

def get_dates(d0, d1):
    out, cur = [], d0
    while cur <= d1:
        out.append(cur); cur += timedelta(days=1)
    return out

def fetch(idx_date):
    idx, d = idx_date
    path = f"{BASE}/sst_{d.strftime('%Y%m%d')}.nc"
    f = fs.open(path, 'rb')
    try:
        ds = xr.open_dataset(f, engine="h5netcdf")
        arr = ds['analysed_sst'].values[:, IL:IL2, IJ:IJ2].astype(np.float64)
        t = ds['time'].values[0]
        ds.close()
        return idx, arr
    finally:
        f.close()

def run_batch(name, d0, d1, workers=8):
    dates = get_dates(d0, d1)
    arr = np.empty((len(dates), 60, 60), dtype=np.float64)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for idx, a in ex.map(lambda p: fetch(p), enumerate(dates)):
            arr[idx] = a
    np.save(f'/work/{name}.npy', arr)
    with open(f'/work/{name}_dates.json', 'w') as f:
        json.dump([d.strftime('%Y-%m-%d') for d in dates], f)
    print(name, "days:", len(dates), "time: %.1f s" % (time.time()-t0), "finite frac: %.4f" % np.isfinite(arr).mean())

run_batch('b2', date(1996,6,16), date(2000,2,1))
run_batch('b3', date(2000,2,2), date(2003,1,5))
run_batch('b4', date(2019,6,1), date(2019,8,31), workers=8)
