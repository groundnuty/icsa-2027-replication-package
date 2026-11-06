import os, datetime as dt, time, fsspec, h5py, numpy as np
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base='/icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/cache', exist_ok=True)
LAT0,LAT1,LON0,LON1 = 322,382,485,545

def fetch(d, wid):
    loc=f'/work/cache/tmp{wid}.nc'
    try:
        with fs.open(f'{base}/sst_{d:%Y%m%d}.nc','rb') as rf, open(loc,'wb') as wf:
            shutil.copyfileobj(rf, wf, 1<<20)
        with h5py.File(loc,'r') as f:
            raw=f['analysed_sst'][0, LAT0:LAT1, LON0:LON1]
            tval=f['time'][0]
        os.remove(loc)
        return (d, tval, np.asarray(raw, dtype=np.int16))
    except Exception as e:
        try: os.remove(loc)
        except Exception: pass
        return (d, None, None)

import shutil
dates=[dt.date(1992,1,1)+dt.timedelta(days=i) for i in range(24)]
t0=time.time()
with ThreadPoolExecutor(max_workers=12) as ex:
    res=list(ex.map(lambda i: fetch(dates[i], i%12), range(len(dates))))
el=time.time()-t0
ok=[r for r in res if r[1] is not None]
print(f'fetched {len(ok)}/{len(dates)} in {el:.2f}s -> {el/len(dates):.3f}s/file; est 4120 files: {el/len(dates)*4120/60:.1f} min')
# check grid consistency of lat/lon across a few files & time values
for d,tv,arr in res[:6]:
    print(d, tv, arr.shape, arr.dtype, 'finite frac', float(np.isfinite(arr.astype('float32')).mean()))
# verify one file's coordinates
with fs.open(f'{base}/sst_19920101.nc','rb') as f, h5py.File(f) as h:
    lat=h['latitude'][LAT0:LAT1]; lon=h['longitude'][LON0:LON1]
    print('1992 lat first/last:', lat[0], lat[-1], 'lon first/last:', lon[0], lon[-1])
