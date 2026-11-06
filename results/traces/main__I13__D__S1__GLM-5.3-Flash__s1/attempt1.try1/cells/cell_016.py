import fsspec, os, numpy as np, h5py, datetime as dt, json, time, traceback

fs = fsspec.filesystem('onedata')
BASE_REMOTE = 'icsa2027_data_20261101T090944Z/s1z'
LOCAL_DIR = '/work/data'
os.makedirs(LOCAL_DIR, exist_ok=True)

def daterange(a, b):
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)

# Baseline years 1992-2002; pool windows extend +/-5 days -> include 1991-12-27 .. 2003-01-05
base_dates = list(daterange(dt.date(1991,12,27), dt.date(2003,1,5)))
tgt_dates  = list(daterange(dt.date(2021,6,1),  dt.date(2021,8,31)))
alldates = base_dates + tgt_dates
print('baseline-window days:', len(base_dates), 'target days:', len(tgt_dates), 'total:', len(alldates))

EXP_LAT = np.arange(0)*1.0  # placeholder
expected_lat = None; expected_lon = None

arr = np.full((len(alldates), 60, 60), np.nan, dtype=np.float32)
ok = np.zeros(len(alldates), dtype=bool)
t0 = time.time()
errs = []
for i, d in enumerate(alldates):
    fname = f"sst_{d.strftime('%Y%m%d')}.nc"
    dst = os.path.join(LOCAL_DIR, fname)
    for attempt in range(3):
        try:
            if not os.path.exists(dst) or os.path.getsize(dst) < 1000:
                tmp = dst + '.tmp'
                if os.path.exists(tmp): os.remove(tmp)
                fs.get(os.path.join(BASE_REMOTE, fname), tmp)
                os.replace(tmp, dst)
            with h5py.File(dst, 'r') as f:
                lat = f['latitude'][130:190].astype(np.float64)
                lon = f['longitude'][78:138].astype(np.float64)
                tv = f['time'][0]
                if expected_lat is None:
                    expected_lat, expected_lon = lat, lon
                elif not (np.array_equal(lat, expected_lat) and np.array_equal(lon, expected_lon)):
                    raise ValueError(f'coord mismatch {fname}')
                got = dt.datetime(1981,1,1) + dt.timedelta(seconds=int(tv))
                got = got.date()
                if got != d:
                    raise ValueError(f'time mismatch {fname}: {got} != {d}')
                arr[i] = f['analysed_sst'][0, 130:190, 78:138]
            ok[i] = True
            break
        except Exception as e:
            if attempt == 2:
                errs.append((d.isoformat(), repr(e)))
                if os.path.exists(dst): os.remove(dst)
            time.sleep(1.0)
    if (i+1) % 500 == 0:
        print(f'{i+1}/{len(alldates)} done, {time.time()-t0:.0f}s')

print('finished in', round(time.time()-t0,1), 's; failures:', len(errs))
for e in errs[:10]: print('FAIL', e)
np.save('/work/extract_dates.npy', np.array([d.isoformat() for d in alldates]))
np.save('/work/extract_sst.npy', arr)
np.save('/work/extract_ok.npy', ok)
print('saved arrays; ok count:', int(ok.sum()))
print('any NaN in baseline window entirely (cell check):', np.isnan(arr[:len(base_dates)]).all(axis=(0,)).sum())
