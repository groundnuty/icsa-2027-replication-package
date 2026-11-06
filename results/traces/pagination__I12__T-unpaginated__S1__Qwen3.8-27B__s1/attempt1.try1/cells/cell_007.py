import fsspec, time, pickle
import xarray as xr
import numpy as np
import datetime as dt

fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z/s1z'

# region index from one file (also grab coordinate values)
with fs.open(root+'/sst_20090601.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
lat_all = ds.latitude.values
lon_all = ds.longitude.values
lat64 = lat_all.astype(np.float64)
lon64 = lon_all.astype(np.float64)
lat_idx = np.where((lat64 >= 56.09-1e-6) & (lat64 <= 57.29+1e-6))[0]
lon_idx = np.where((lon64 >= 10.55-1e-6) & (lon64 <= 11.75+1e-6))[0]
ds.close()
print('region lat count', len(lat_idx), 'lon count', len(lon_idx))
print('lat slice:', lat_all[lat_idx[0]].item(), '->', lat_all[lat_idx[-1]].item())
print('lon slice:', lon_all[lon_idx[0]].item(), '->', lon_all[lon_idx[-1]].item())

meta = {'lat_idx': lat_idx, 'lon_idx': lon_idx,
        'lat_vals': lat_all[lat_idx], 'lon_vals': lon_all[lon_idx]}
with open('/tmp/region_meta.pkl','wb') as fh:
    pickle.dump(meta, fh)

def date_range(a, b):
    out = []
    d = a
    while d <= b:
        out.append(d)
        d += dt.timedelta(days=1)
    return out

base_dates = date_range(dt.date(1991,12,27), dt.date(2003,1,5))
tgt_dates  = date_range(dt.date(2009,6,1),  dt.date(2009,8,31))
print('n base', len(base_dates), 'n tgt', len(tgt_dates))

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

# chunk 1: first half of baseline
load_chunk(base_dates[:2014], '/tmp/base_a.npz', meta)