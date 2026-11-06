import fsspec, os, time, pickle, numpy as np, xarray as xr
from concurrent.futures import ThreadPoolExecutor, as_completed

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/dl', exist_ok=True)

with open('/work/dates.pkl','rb') as f:
    dd = pickle.load(f)
base_dates = dd['base']; tgt_dates = dd['tgt']

# region mask from known grid (verified): lat 53.5..66.0 step .02, lon 9.0..30.0 step .02
LAT = (np.arange(626) * 0.02 + 53.5)
LON = (np.arange(1051) * 0.02 + 9.0)
latm = (LAT >= 61.57) & (LAT <= 62.77)
lonm = (LON >= 20.17) & (LON <= 21.37)
print("region cells:", latm.sum(), lonm.sum())

def extract(d):
    """download one file, extract region, return (ymdstr, 60x60 float32 array or None if file missing)"""
    s = d.strftime('%Y%m%d')
    p = f'/work/dl/sst_{s}.nc'
    try:
        if not os.path.exists(p):
            fs.get(base + f'/sst_{s}.nc', p)
        ds = xr.open_dataset(p, engine='h5netcdf')
        arr = ds['analysed_sst'].values[0].astype('float32')
        # verify coordinates match expectation
        lat = ds['latitude'].values
        lon = ds['longitude'].values
        tval = ds['time'].values[0]
        ok = (np.array_equal(lat, LAT) and np.array_equal(lon, LON)
              and np.datetime64(tval) == np.datetime64(d.isoformat(), 'D'))
        sub = arr[latm][:, lonm].copy()
        ds.close()
        os.remove(p)
        if not ok:
            return (s, None, 'COORD/TIME MISMATCH')
        return (s, sub, None)
    except Exception as e:
        return (s, None, f'ERR {type(e).__name__}: {str(e)[:100]}')

all_dates = base_dates + tgt_dates
def process_batch(dates):
    results = {}
    errors = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = [ex.submit(extract, d) for d in dates]
        for fu in as_completed(futs):
            s, sub, err = fu.result()
            if err: errors.append((s, err))
            else: results[s] = sub
    return results, errors

def save_batch(results, path):
    with open(path, 'wb') as f:
        pickle.dump(results, f)

t0 = time.time()
results, errors = process_batch(all_dates[:800])
save_batch(results, '/work/batch0.pkl')
print(f"batch0: {len(results)}/800 ok, {len(errors)} errors in {time.time()-t0:.1f}s")
for s, e in errors[:10]: print(" ", s, e)
