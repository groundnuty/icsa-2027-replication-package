
import fsspec, xarray as xr, numpy as np, time, datetime as dt
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
BASE = '/icsa2027_data_20261101T090944Z/s1z'

def read_slice_retried(datestr, tries=4):
    last = None
    for i in range(tries):
        try:
            p = f"{BASE}/sst_{datestr}.nc"
            f = fs.open(p, "rb")
            try:
                ds = xr.open_dataset(f, engine="h5netcdf")
                v = ds['analysed_sst'].isel(latitude=slice(217,277), longitude=slice(421,481)).values.astype(np.float64).squeeze(axis=0)
                return v
            finally:
                f.close()
        except Exception as e:
            last = e
            time.sleep(1.0 + i)
    raise RuntimeError(f"failed {datestr}: {last}")

bdates = [dt.date(1991,12,27) + dt.timedelta(days=i) for i in range(4028)]
CH = 500
t0=time.time()
chunk = [bdates[i:i+CH] for i in range(0, 4028, CH)]
print("chunks:", len(chunk), [len(c) for c in chunk])

# do first chunk now, test speed
def work(d):
    return read_slice_retried(d.strftime('%Y%m%d'))
with ThreadPoolExecutor(max_workers=24) as ex:
    vals = list(ex.map(work, chunk[0]))
arr = np.stack(vals, axis=0)
np.save('/tmp/mhw/baseline_part0.npy', arr)
print("part0 done:", arr.shape, "in", time.time()-t0, "s")
print("finite per day (min/max):", np.isfinite(arr).min(axis=(1,2)).min(), np.isfinite(arr).max(axis=(1,2)).max())
