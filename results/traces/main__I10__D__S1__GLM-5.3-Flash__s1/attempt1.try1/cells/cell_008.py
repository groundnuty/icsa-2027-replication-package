import numpy as np, xarray as xr, os, datetime as dt, time, pickle
import fsspec
from concurrent.futures import ThreadPoolExecutor

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
lat_idx = np.load('/work/lat_idx.npy'); lon_idx = np.load('/work/lon_idx.npy')
with xr.open_dataset('/work/tmp/sample.nc', engine='h5netcdf') as ds:
    lat_ref = ds['latitude'].values; lon_ref = ds['longitude'].values

ext_start, ext_end = dt.date(1991,12,27), dt.date(2003,1,5)
allC = [ext_start + dt.timedelta(i) for i in range((ext_end-ext_start).days+1)]
dstrs = [d.strftime('%Y%m%d') for d in allC]

def extract(dstr):
    local = f'/work/bt/f_{dstr}.nc'
    try:
        fs.get(f'{base}/sst_{dstr}.nc', local)
        with xr.open_dataset(local, engine='h5netcdf') as ds:
            ntime = ds.sizes.get('time')
            tv = ds['time'].values
            arr = ds['analysed_sst'].isel(time=0, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)
            g_ok = (ds['latitude'].values.tobytes()==lat_ref.tobytes()) and (ds['longitude'].values.tobytes()==lon_ref.tobytes())
        os.remove(local)
        return (dstr, 'OK', str(tv[0])[:10], ntime, g_ok, arr)
    except Exception as e:
        try: os.remove(local)
        except Exception: pass
        return (dstr, 'ERR', repr(e)[:100], None, None, None)

t0=time.time()
results = {}
B = 400
for bi in range(0, len(dstrs), B):
    batch = dstrs[bi:bi+B]
    with ThreadPoolExecutor(8) as ex:
        for out in ex.map(extract, batch):
            results[out[0]] = out
    print(f'batch {bi//B+1}: cumulative {len(results)}', flush=True)
print('elapsed:', round(time.time()-t0,1))

errs = [k for k,v in results.items() if v[1]=='ERR']
grid_bad = [k for k,v in results.items() if v[1]=='OK' and not v[4]]
ntime_bad = [k for k,v in results.items() if v[1]=='OK' and v[3]!=1]
time_bad = [k for k,v in results.items() if v[1]=='OK' and v[2]!=k[:4]+'-'+k[4:6]+'-'+k[6:]]
print('errors:', len(errs), errs[:10])
print('grid mismatches:', len(grid_bad), grid_bad[:5])
print('ntime!=1:', len(ntime_bad), 'time!=filename:', len(time_bad), time_bad[:5])
missing = [d for d in dstrs if d not in results]
print('missing files:', len(missing), missing[:10])

# stack in date order
Barr = np.stack([results[d][5] for d in dstrs]) if not missing and not errs else None
print('Barr:', None if Barr is None else Barr.shape)
np.save('/work/baseline_sst.npy', Barr)
with open('/work/baseline_meta.pkl','wb') as f:
    pickle.dump({'dstrs': dstrs, 'errs': errs, 'grid_bad': grid_bad, 'time_bad': time_bad,
                 'missing': missing, 'ntime_bad': ntime_bad}, f)
print('finite frac:', np.isfinite(Barr).mean())
print('min/max:', np.nanmin(Barr), np.nanmax(Barr))
