import fsspec, h5py, numpy as np, datetime as dt, time, os
from concurrent.futures import ThreadPoolExecutor

fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'
i0,i1,j0,j1 = 491,550,616,675  # verified indices (inclusive)

d0 = dt.date(1991,12,27); d1 = dt.date(2003,1,5)
bl_dates = [d0 + dt.timedelta(days=k) for k in range((d1-d0).days+1)]
tg0 = dt.date(2009,6,1); tg1 = dt.date(2009,8,31)
tg_dates = [tg0 + dt.timedelta(days=k) for k in range((tg1-tg0).days+1)]
print('baseline days', len(bl_dates), bl_dates[0], bl_dates[-1])
print('target days', len(tg_dates), tg_dates[0], tg_dates[-1])

def fetch(dates, tag):
    nlat, nlon = i1-i0+1, j1-j0+1
    out = np.empty((len(dates), nlat, nlon), dtype='float32')
    times = np.empty(len(dates), dtype='int64')
    fails = []
    def work(k):
        for attempt in range(3):
            try:
                ds_ = dates[k].strftime('%Y%m%d')
                with fs.open(f'{base}/sst_{ds_}.nc','rb') as f:
                    with h5py.File(f,'r') as hf:
                        sub = hf['analysed_sst'][0, i0:i1+1, j0:j1+1]
                        t = int(hf['time'][0])
                return k, np.asarray(sub, dtype='float32'), t
            except Exception as e:
                if attempt==2: fails.append((k, str(e)[:100]))
                time.sleep(1+attempt)
        return k, None, -1
    t0=time.time()
    with ThreadPoolExecutor(8) as ex:
        for k, sub, t in ex.map(work, range(len(dates))):
            if sub is not None:
                out[k]=sub; times[k]=t
            if (k+1) % 500 == 0:
                print(f'{tag} {k+1}/{len(dates)} elapsed {time.time()-t0:.0f}s fails={len(fails)}', flush=True)
    print(f'{tag} done in {time.time()-t0:.0f}s, fails={len(fails)}')
    return out, times, fails

bl, blt, f1 = fetch(bl_dates, 'BL')
np.save('bl_sst.npy', bl); np.save('bl_times.npy', blt)
tg, tgt, f2 = fetch(tg_dates, 'TG')
np.save('tg_sst.npy', tg); np.save('tg_times.npy', tgt)

# verify time values match filename dates (1981-01-01 epoch)
import pandas as pd
epoch = pd.Timestamp('1981-01-01')
for name, arr_t, dates in [('BL',blt,bl_dates), ('TG',tgt,tg_dates)]:
    ok = all(epoch + pd.Timedelta(seconds=int(t)) == pd.Timestamp(d) for t,d in zip(arr_t,dates))
    print(name, 'time-filename match:', ok)

blf = np.load('bl_sst.npy'); tgf = np.load('tg_sst.npy')
print('BL shape', blf.shape, 'TG shape', tgf.shape)
# sea cells: finite on every target day
sea = np.isfinite(tgf).all(axis=0)
land = np.isfinite(tgf).sum(axis=0)==0
partial = (~sea) & (~land)
print('sea cells', int(sea.sum()), 'all-NaN cells', int(land.sum()), 'partial cells', int(partial.sum()))
print('BL finite frac', float(np.isfinite(blf).mean()), 'TG finite frac', float(np.isfinite(tgf).mean()))
# how many baseline days fully NaN (whole region)?
nd = np.isfinite(blf).sum(axis=(1,2))
print('BL days with zero finite cells:', int((nd==0).sum()), 'min finite/day', int(nd.min()), 'max', int(nd.max()))
