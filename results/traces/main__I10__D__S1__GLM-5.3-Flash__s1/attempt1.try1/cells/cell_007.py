import numpy as np, xarray as xr, os, datetime as dt, json, time
import fsspec
from concurrent.futures import ThreadPoolExecutor

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/bt', exist_ok=True)

lat_idx = np.load('/work/lat_idx.npy'); lon_idx = np.load('/work/lon_idx.npy')

# reference grid from sample
with xr.open_dataset('/work/tmp/sample.nc', engine='h5netcdf') as ds:
    lat_ref = ds['latitude'].values; lon_ref = ds['longitude'].values

# verify grid identity + time coord on the 8 test files spanning years
test_dates = ['19911227','19920101','19950715','19980115','20000229','20021231','20030105','20050601']
for d in test_dates:
    with xr.open_dataset(f'/work/tmp/test_{d}.nc', engine='h5netcdf') as ds:
        g_ok = (ds['latitude'].values.tobytes()==lat_ref.tobytes()) and (ds['longitude'].values.tobytes()==lon_ref.tobytes())
        tv = ds['time'].values
        print(d, 'grid_ok:', g_ok, 'ntime:', ds.sizes.get('time'), 'time:', str(tv[0])[:10],
              'var:', list(ds.data_vars))

# date lists
CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
def mdoy(d):
    return CUM[d.month-1] + d.day
# sanity of mapping
assert mdoy(dt.date(2005,1,1))==1 and mdoy(dt.date(1992,2,28))==59 and mdoy(dt.date(1992,2,29))==60
assert mdoy(dt.date(1993,3,1))==61 and mdoy(dt.date(2005,12,31))==366
assert mdoy(dt.date(2005,6,1))==153 and mdoy(dt.date(2005,8,31))==244
print('mdoy mapping OK')

base_start, base_end = dt.date(1992,1,1), dt.date(2002,12,31)
ext_start, ext_end = dt.date(1991,12,27), dt.date(2003,1,5)
allC = [ext_start + dt.timedelta(i) for i in range((ext_end-ext_start).days+1)]
target_dates = [dt.date(2005,6,1) + dt.timedelta(i) for i in range((dt.date(2005,8,31)-dt.date(2005,6,1)).days+1)]
print('baseline candidate dates:', len(allC), allC[0], allC[-1], '| target days:', len(target_dates))

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
        return (dstr, 'ERR', repr(e)[:120], None, None, None)

# --- target period ---
t0 = time.time()
res = {}
with ThreadPoolExecutor(8) as ex:
    for out in ex.map(extract, [d.strftime('%Y%m%d') for d in target_dates]):
        res[out[0]] = out
errs = [k for k,v in res.items() if v[1]=='ERR']
grid_bad = [k for k,v in res.items() if v[1]=='OK' and not v[4]]
ntime_bad = [k for k,v in res.items() if v[1]=='OK' and v[3]!=1]
time_bad = [k for k,v in res.items() if v[1]=='OK' and v[2]!=k[:4]+'-'+k[4:6]+'-'+k[6:]]
print('target: n=', len(res), 'errors:', len(errs), errs[:5])
print('grid mismatches:', len(grid_bad), 'ntime!=1:', len(ntime_bad), 'time!=filename:', len(time_bad))
T = np.stack([res[d.strftime('%Y%m%d')][5] for d in target_dates])  # (92,60,60)
np.save('/work/target_sst.npy', T)
np.save('/work/target_datestr.npy', np.array([d.strftime('%Y%m%d') for d in target_dates]))
print('target array:', T.shape, T.dtype, 'finite frac:', np.isfinite(T).mean())
print('SST range target:', np.nanmin(T), np.nanmax(T))
print('cells finite all 92 days:', int(np.isfinite(T).all(axis=0).sum()), 'of', T[0].size)
print('elapsed:', round(time.time()-t0,1), 's')
