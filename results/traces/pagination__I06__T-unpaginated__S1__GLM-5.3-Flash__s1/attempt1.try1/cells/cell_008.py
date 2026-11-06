import numpy as np, datetime as dt, fsspec, h5py, time, os, pickle
from concurrent.futures import ThreadPoolExecutor

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
lat0,lat1,lon0,lon1 = 48,108,353,413

def daterange(a,b):
    d0=dt.date(*map(int,a.split('-'))); d1=dt.date(*map(int,b.split('-')))
    out=[]; d=d0
    while d<=d1:
        out.append(d); d+=dt.timedelta(days=1)
    return out

base_dates = daterange('1991-12-27','2003-01-05')      # baseline years + spillover
targ_dates = daterange('2012-06-01','2012-08-31')
print("baseline-window days:", len(base_dates), base_dates[0], base_dates[-1])
print("target days:", len(targ_dates), targ_dates[0], targ_dates[-1])

def read_sub(d):
    ds = f"sst_{d.strftime('%Y%m%d')}.nc"
    with fs.open(f"{base}/{ds}",'rb') as f:
        with h5py.File(f,'r') as h:
            return h['analysed_sst'][0, lat0:lat1, lon0:lon1], int(h['time'][0])

t0=time.time()
with ThreadPoolExecutor(16) as ex:
    res_b = list(ex.map(read_sub, base_dates))
    res_t = list(ex.map(read_sub, targ_dates))
print("read time sec:", time.time()-t0)

base_sst = np.stack([r[0] for r in res_b])   # (nb, 60, 60) float32
base_tsec = np.array([r[1] for r in res_b], dtype=np.int64)
targ_sst = np.stack([r[0] for r in res_t])
targ_tsec = np.array([r[1] for r in res_t], dtype=np.int64)
print("base_sst", base_sst.shape, base_sst.dtype, "targ_sst", targ_sst.shape)

# verify time values match filenames
ref = np.datetime64('1981-01-01T00:00:00')
ok_b = all((ref + np.timedelta64(int(s),'s')).astype('datetime64[D]').astype(dt.date) == d
           for s,d in zip(base_tsec, base_dates))
ok_t = all((ref + np.timedelta64(int(s),'s')).astype('datetime64[D]').astype(dt.date) == d
           for s,d in zip(targ_tsec, targ_dates))
print("time coords match filenames:", ok_b, ok_t)

np.save('/tmp/base_sst.npy', base_sst)
np.save('/tmp/targ_sst.npy', targ_sst)
with open('/tmp/meta.pkl','wb') as f:
    pickle.dump({'base_dates':[d.isoformat() for d in base_dates],
                 'targ_dates':[d.isoformat() for d in targ_dates],
                 'base_tsec':base_tsec, 'targ_tsec':targ_tsec}, f)
print("finite frac base:", np.isfinite(base_sst).mean(), " target:", np.isfinite(targ_sst).mean())
# sea cells
sea = np.isfinite(targ_sst).all(axis=0)
print("sea cells:", sea.sum(), "of", sea.size)
