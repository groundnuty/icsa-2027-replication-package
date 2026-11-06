import fsspec, os, time, pickle, numpy as np, xarray as xr
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/dl', exist_ok=True)

with open('/work/dates.pkl','rb') as f:
    dd = pickle.load(f)
base_dates = dd['base']; tgt_dates = dd['tgt']

# reference grid from a known-good 2021 file
ds0 = xr.open_dataset('/work/data/sst_20210601.nc', engine='h5netcdf')
LAT = ds0['latitude'].values.astype('float64')
LON = ds0['longitude'].values.astype('float64')
ds0.close()
latm = (LAT >= 61.57) & (LAT <= 62.77)
lonm = (LON >= 20.17) & (LON <= 21.37)

def find_idx(coord, ref):
    d = np.abs(coord - ref)
    return d.argmin()

def extract(d):
    s = d.strftime('%Y%m%d')
    p = f'/work/dl/sst_{s}.nc'
    try:
        if not os.path.exists(p):
            fs.get(base + f'/sst_{s}.nc', p)
        ds = xr.open_dataset(p, engine='h5netcdf')
        lat = ds['latitude'].values.astype('float64')
        lon = ds['longitude'].values.astype('float64')
        tval = np.datetime64(ds['time'].values[0])
        # tolerance match: nearest index, must be within 0.005
        li = find_idx(lat, LAT); lo = find_idx(lon, LON)
        if abs(lat[li]-LAT[li]) > 0.005 or abs(lon[lo]-LON[lo]) > 0.005 or lat.shape != LAT.shape or lon.shape != LON.shape:
            ds.close()
            return (s, None, 'COORD MISMATCH')
        if tval != np.datetime64(d.isoformat(), 'D'):
            ds.close()
            return (s, None, f'TIME MISMATCH {tval}')
        arr = ds['analysed_sst'].values[0].astype('float32')
        sub = arr[latm][:, lonm].copy()
        ds.close()
        os.remove(p)
        return (s, sub, None)
    except Exception as e:
        return (s, None, f'ERR {type(e).__name__}: {str(e)[:80]}')

def process_batch(dates):
    results = {}; errors = []
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

all_dates = base_dates + tgt_dates
t0 = time.time()
results, errors = process_batch(all_dates[:800])
save_batch(results, '/work/batch0.pkl')
print(f"batch0: {len(results)}/800 ok, {len(errors)} errors in {time.time()-t0:.1f}s")
for s, e in errors[:10]: print(" ", s, e)
os.remove('/work/dl/dbg.nc') if os.path.exists('/work/dl/dbg.nc') else None
