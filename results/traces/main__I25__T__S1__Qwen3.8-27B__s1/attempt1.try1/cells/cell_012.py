
import fsspec, io, time, os, numpy as np, xarray as xr
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base='/icsa2027_data_20261101T090944Z/s1z/'
import datetime as dt
def dlist(start, end):
    d0, d1 = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    return [d0 + dt.timedelta(days=i) for i in range((d1-d0).days+1)]
bdates = dlist('1991-12-27','2003-01-05')
tdates = dlist('2016-06-01','2016-08-31')
NB, NT = len(bdates), len(tdates)
print("NB, NT:", NB, NT)

def fetch_parse(d):
    name = f"sst_{d.strftime('%Y%m%d')}.nc"
    last = None
    for attempt in range(6):
        try:
            raw = fs.cat_file(base+name)
            ds = xr.open_dataset(io.BytesIO(raw), engine='h5netcdf')
            lat = ds.latitude.values; lon = ds.longitude.values
            ilat = np.where((lat>=57.57-1e-9)&(lat<=58.77+1e-9))[0]
            ilon = np.where((lon>=10.25-1e-9)&(lon<=11.45+1e-9))[0]
            assert ilat.shape==(60,) and ilon.shape==(60,), (name, ilat.shape, ilon.shape)
            tval = ds.time.values[0]
            assert np.datetime64(tval) == np.datetime64(d.isoformat()), (name, tval)
            sub = ds.analysed_sst.values[0, ilat[0]:ilat[-1]+1, ilon[0]:ilon[-1]+1].astype(np.float64).ravel()
            ds.close()
            return sub
        except Exception as e:
            last = e
            time.sleep(0.5*(attempt+1))
    raise RuntimeError(f"{name}: {last}")

t0=time.time()
sst_base = np.empty((NB, 3600), dtype=np.float64)
with ThreadPoolExecutor(max_workers=8) as ex:
    for i, sub in enumerate(ex.map(fetch_parse, bdates, chunksize=16)):
        sst_base[i] = sub
        if (i+1) % 1000 == 0:
            np.save('/tmp/sst_base.npy', sst_base)
            print(i+1, "of", NB, "done, %.0f s elapsed" % (time.time()-t0), flush=True)
np.save('/tmp/sst_base.npy', sst_base)
print("base done in %.0f s" % (time.time()-t0))
nan_rows = np.where(~np.isfinite(sst_base).all(axis=1))[0]
print("rows with any NaN:", len(nan_rows), nan_rows[:10])
t0=time.time()
sst_tgt = np.empty((NT, 3600), dtype=np.float64)
with ThreadPoolExecutor(max_workers=8) as ex:
    for i, sub in enumerate(ex.map(fetch_parse, tdates, chunksize=8)):
        sst_tgt[i] = sub
np.save('/tmp/sst_tgt.npy', sst_tgt)
print("target done in %.0f s" % (time.time()-t0))
print("base shape", sst_base.shape, sst_base.dtype, "tgt shape", sst_tgt.shape)
np.save('/tmp/bdates.npy', np.array([d.toordinal() for d in bdates]))
np.save('/tmp/tdates.npy', np.array([d.toordinal() for d in tdates]))
print("saved")
