
import os, json
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor
import numpy as np, fsspec, xarray as xr, time

print("marker:", open('/work/marker.txt').read())

BASE = '/icsa2027_data_20261101T090944Z/s1z'
fs = fsspec.filesystem('onedata')
IL, IL2 = 545, 605  # lat slice [545, 605)
IJ, IJ2 = 721, 781  # lon slice [721, 781)

def get_dates(d0, d1):
    out = []
    cur = d0
    while cur <= d1:
        out.append(cur)
        cur += timedelta(days=1)
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
        return idx, arr, str(np.datetime64(t, 'D'))
    finally:
        f.close()

def run_batch(name, d0, d1, workers=8):
    dates = get_dates(d0, d1)
    arr = np.empty((len(dates), 60, 60), dtype=np.float64)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for idx, a, iso in ex.map(lambda p: fetch(p), enumerate(dates)):
            arr[idx] = a
    np.save(f'/work/{name}.npy', arr)
    with open(f'/work/{name}_dates.json', 'w') as f:
        json.dump([d.strftime('%Y-%m-%d') for d in dates], f)
    print(name, "days:", len(dates), "time: %.1f s" % (time.time()-t0), "shape:", arr.shape, "finite frac: %.4f" % np.isfinite(arr).mean())

# batch 1
run_batch('b1', date(1991,12,27), date(1996,6,15))
