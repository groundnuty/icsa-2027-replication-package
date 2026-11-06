import fsspec, xarray as xr, numpy as np, datetime as dt, time
from concurrent.futures import ThreadPoolExecutor

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
I0, I1, J0, J1 = 34, 94, 213, 273

def daterange(a, b):
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)

base_days = list(daterange(dt.date(1991,12,27), dt.date(2003,1,5)))
tgt_days  = list(daterange(dt.date(2004,6,1),  dt.date(2004,8,31)))
all_days = base_days + tgt_days
print("n base:", len(base_days), "n tgt:", len(tgt_days))

def read_one(d):
    p = f'{base}/sst_{d:%Y%m%d}.nc'
    last = None
    for attempt in range(4):
        try:
            with fs.open(p, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                v = np.asarray(ds['analysed_sst'].isel(time=0).values[I0:I1, J0:J1], dtype=np.float32)
                tv = ds['time'].values[0]
                ds.close()
            return v, np.datetime64(tv, 'D')
        except Exception as e:
            last = e
            time.sleep(1.5)
    raise RuntimeError(f"{d}: {last}")

t0 = time.time()
results = [None]*len(all_days)
with ThreadPoolExecutor(16) as ex:
    futs = {ex.submit(read_one, d): k for k, d in enumerate(all_days)}
    done = 0
    for fu in __import__('concurrent.futures', fromlist=['as_completed']).as_completed(futs):
        k = futs[fu]
        results[k] = fu.result()
        done += 1
        if done % 1000 == 0:
            print(f"{done}/{len(all_days)} files, {time.time()-t0:.1f}s", flush=True)
print(f"read done: {time.time()-t0:.1f}s")

base_data = np.stack([results[k][0] for k in range(len(base_days))])
tgt_data  = np.stack([results[k][0] for k in range(len(base_days), len(all_days))])
base_t = np.array([results[k][1] for k in range(len(base_days))], dtype='datetime64[D]')
tgt_t  = np.array([results[k][1] for k in range(len(base_days), len(all_days))], dtype='datetime64[D]')

mism = [(str(base_t[k]), str(base_days[k])) for k in range(len(base_days)) if base_t[k] != np.datetime64(base_days[k])]
mism += [(str(tgt_t[k]), str(tgt_days[k])) for k in range(len(tgt_days)) if tgt_t[k] != np.datetime64(tgt_days[k])]
print("time mismatches:", mism[:10], "count:", len(mism))

lat = results[0][0]  # placeholder
np.savez('mhw_cache.npz', base_data=base_data, tgt_data=tgt_data,
         base_t=base_t, tgt_t=tgt_t)
print("cached shapes:", base_data.shape, tgt_data.shape, base_data.dtype)
print("finite frac base:", np.isfinite(base_data).mean(), "tgt:", np.isfinite(tgt_data).mean())
