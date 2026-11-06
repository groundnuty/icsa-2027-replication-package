import fsspec, xarray as xr, numpy as np, datetime as dt, os, time, json, shutil
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
I0, I1, J0, J1 = 109, 168, 373, 432
print('cwd', os.getcwd(), '| disk', shutil.disk_usage(os.getcwd()))

def daterange(a, b):
    return [a + dt.timedelta(days=i) for i in range((b - a).days + 1)]

dates_ext = daterange(dt.date(1991,12,27), dt.date(2003,1,5))
dates_tgt = daterange(dt.date(2021,6,1), dt.date(2021,8,31))
print('ext days', len(dates_ext), dates_ext[0], dates_ext[-1], '| tgt days', len(dates_tgt), dates_tgt[0], dates_tgt[-1])

def read_one(d, retries=4):
    fn = f"sst_{d:%Y%m%d}.nc"
    last = None
    for k in range(retries):
        try:
            f = fs.open(base + '/' + fn, 'rb')
            ds = xr.open_dataset(f, engine='h5netcdf')
            t = ds['time'].values[0]
            v = ds['analysed_sst'][0, I0:I1+1, J0:J1+1].values.astype(np.float64)
            lat = ds['latitude'].values; lon = ds['longitude'].values
            ds.close(); f.close()
            if str(t)[:10] != d.isoformat():
                raise ValueError(f"time mismatch {fn}: {t}")
            return v, lat, lon
        except Exception as e:
            last = e; time.sleep(0.5)
    raise RuntimeError(f"{fn}: {last!r}")

t0 = time.time()
lat_ref = lon_ref = None
ext = np.empty((len(dates_ext), 60, 60), dtype=np.float64)
for i, d in enumerate(dates_ext):
    v, lat, lon = read_one(d)
    if lat_ref is None:
        lat_ref, lon_ref = lat.copy(), lon.copy()
    else:
        assert np.array_equal(lat, lat_ref) and np.array_equal(lon, lon_ref), d
    ext[i] = v
    if (i+1) % 1000 == 0:
        print('ext', i+1, '%.0f s' % (time.time()-t0), flush=True)
print('ext read done:', ext.shape, '%.0f s' % (time.time()-t0), flush=True)

tgt = np.empty((len(dates_tgt), 60, 60), dtype=np.float64)
for i, d in enumerate(dates_tgt):
    v, lat, lon = read_one(d)
    assert np.array_equal(lat, lat_ref) and np.array_equal(lon, lon_ref), d
    tgt[i] = v
print('tgt read done:', tgt.shape, '%.0f s' % (time.time()-t0), flush=True)

os.makedirs('cache', exist_ok=True)
np.save('cache/ext.npy', ext)
np.save('cache/tgt.npy', tgt)
with open('cache/meta.json','w') as fh:
    json.dump({'dates_ext':[d.isoformat() for d in dates_ext],
               'dates_tgt':[d.isoformat() for d in dates_tgt],
               'lat': lat_ref.astype(float).tolist(),
               'lon': lon_ref.astype(float).tolist()}, fh)

# coverage diagnostics
fin_tgt = np.isfinite(tgt)          # (92,60,60)
sea = fin_tgt.all(axis=0)
land = (~np.isfinite(tgt)).all(axis=0)
partial = (~sea) & (~land)
print('cells total 3600 | sea:', sea.sum(), '| all-NaN (land):', land.sum(), '| partial:', partial.sum())
fin_ext = np.isfinite(ext)
cnt_ext = fin_ext.sum(axis=0)
print('ext finite count per cell: min', cnt_ext.min(), 'max', cnt_ext.max())
print('sea cells with any missing ext day:', (cnt_ext[sea] < len(dates_ext)).sum())
print('sea cells with all ext days finite:', (cnt_ext[sea] == len(dates_ext)).sum())
if partial.sum():
    pi = np.argwhere(partial)
    print('partial cells (first 10):', pi[:10].tolist(), 'their target finite counts:',
          [int(fin_tgt[:, r, c].sum()) for r, c in pi[:10]])
# NaN pattern static? compare land mask of first and last ext days
lm0 = ~np.isfinite(ext[0]); lm1 = ~np.isfinite(ext[-1]); lmT = ~np.isfinite(tgt[0])
print('land mask identical first/last ext & first tgt:', np.array_equal(lm0, lm1) and np.array_equal(lm0, lmT))
print('sst range over sea target:', np.nanmin(tgt[:, sea]), np.nanmax(tgt[:, sea]))
