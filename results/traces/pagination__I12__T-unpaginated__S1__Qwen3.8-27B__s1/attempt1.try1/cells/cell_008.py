import fsspec, time, pickle
import xarray as xr
import numpy as np
import datetime as dt

fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z/s1z'
meta = pickle.load(open('/tmp/region_meta.pkl','rb'))

def date_range(a, b):
    out = []
    d = a
    while d <= b:
        out.append(d)
        d += dt.timedelta(days=1)
    return out

base_dates = date_range(dt.date(1991,12,27), dt.date(2003,1,5))
tgt_dates  = date_range(dt.date(2009,6,1),  dt.date(2009,8,31))

def load_chunk(dates, out_path, meta):
    li, lj = meta['lat_idx'], meta['lon_idx']
    arr = np.empty((len(dates), len(li), len(lj)), dtype=np.float64)
    times = np.empty(len(dates), dtype='datetime64[ns]')
    t0 = time.time()
    for i, d in enumerate(dates):
        fn = root+f"/sst_{d:%Y%m%d}.nc"
        with fs.open(fn,'rb') as f:
            ds = xr.open_dataset(f, engine='h5netcdf')
            a = ds.analysed_sst.values[0]
            arr[i] = a[li][:, lj].astype(np.float64)
            times[i] = ds.time.values[0]
            ds.close()
        if (i+1) % 500 == 0:
            print(f'  {i+1}/{len(dates)}  {time.time()-t0:.0f}s', flush=True)
    np.savez_compressed(out_path, dates=np.array([str(d) for d in dates]), arr=arr, times=times)
    print('saved', out_path, f'{time.time()-t0:.0f}s total', flush=True)

load_chunk(base_dates[2014:], '/tmp/base_b.npz', meta)
load_chunk(tgt_dates, '/tmp/tgt.npz', meta)