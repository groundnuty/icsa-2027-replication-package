import fsspec, h5py, numpy as np, datetime as dt, time, os

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
i0,i1,j0,j1 = 404,463,559,618
NI, NJ = i1-i0+1, j1-j0+1

def daterange(a, b):
    d = a; out=[]
    while d <= b:
        out.append(d); d += dt.timedelta(days=1)
    return out

base_dates = daterange(dt.date(1991,12,27), dt.date(2003,1,5))
tgt_dates  = daterange(dt.date(2009,6,1),  dt.date(2009,8,31))
print('base days', len(base_dates), 'tgt days', len(tgt_dates))

def read_sub(path):
    for attempt in range(3):
        try:
            with fs.open(path,'rb') as f:
                with h5py.File(f,'r') as hf:
                    a = hf['analysed_sst'][0, i0:i1+1, j0:j1+1]
                    tsec = hf['time'][0]
            return np.asarray(a, dtype=np.float64), int(tsec)
        except Exception as e:
            if attempt == 2: raise
            time.sleep(1.0)

# sanity: lat/lon identical between an early and late file
with fs.open(f'{base}/sst_19920101.nc','rb') as f:
    with h5py.File(f,'r') as hf:
        la1 = hf['latitude'][:]; lo1 = hf['longitude'][:]
with fs.open(f'{base}/sst_20090601.nc','rb') as f:
    with h5py.File(f,'r') as hf:
        la2 = hf['latitude'][:]; lo2 = hf['longitude'][:]
print('lat/lon static:', np.array_equal(la1,la2), np.array_equal(lo1,lo2))
np.save('lat.npy', np.asarray(la1, dtype=np.float32))
np.save('lon.npy', np.asarray(lo1, dtype=np.float32))

EPOCH = np.datetime64('1981-01-01')
t0 = time.time(); errs = 0
Sb = np.empty((len(base_dates), NI, NJ), dtype=np.float64)
for k, d in enumerate(base_dates):
    a, ts = read_sub(f'{base}/sst_{d:%Y%m%d}.nc')
    dec = EPOCH + np.timedelta64(ts,'s')
    if str(dec)[:10] != d.isoformat():
        print('TIME MISMATCH', d, dec); errs += 1
    Sb[k] = a
    if (k+1) % 1000 == 0: print('base %d/%d  %.1fs' % (k+1, len(base_dates), time.time()-t0))
print('baseline done %.1fs, mismatches=%d' % (time.time()-t0, errs))

St = np.empty((len(tgt_dates), NI, NJ), dtype=np.float64)
for k, d in enumerate(tgt_dates):
    a, ts = read_sub(f'{base}/sst_{d:%Y%m%d}.nc')
    dec = EPOCH + np.timedelta64(ts,'s')
    if str(dec)[:10] != d.isoformat():
        print('TIME MISMATCH', d, dec); errs += 1
    St[k] = a
print('target done %.1fs, total mismatches=%d' % (time.time()-t0, errs))

np.save('Sb.npy', Sb); np.save('St.npy', St)
np.save('base_dates.npy', np.array([np.datetime64(d) for d in base_dates]))
np.save('tgt_dates.npy',  np.array([np.datetime64(d) for d in tgt_dates]))
print('saved. shapes', Sb.shape, St.shape)
print('target finite cells (all 92 days):', int(np.isfinite(St).all(axis=0).sum()))
