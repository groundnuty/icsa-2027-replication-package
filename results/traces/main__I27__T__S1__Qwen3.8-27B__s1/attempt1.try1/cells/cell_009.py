
import fsspec, xarray as xr, numpy as np, time
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
BASE = '/icsa2027_data_20261101T090944Z/s1z'

def read_slice(datestr):
    p = f"{BASE}/sst_{datestr}.nc"
    f = fs.open(p, "rb")
    try:
        ds = xr.open_dataset(f, engine="h5netcdf")
        v = ds['analysed_sst'].isel(latitude=slice(217,277), longitude=slice(421,481)).values.astype(np.float64)
        lat = ds['latitude'].values.copy()
        lon = ds['longitude'].values.copy()
        t = ds['time'].values[0]
        return datestr, v, lat, lon
    finally:
        f.close()

dates = ['2008%02d%02d' % (m,d) for m,d in [(6,d) for d in range(1,31)] + [(7,d) for d in range(1,32)] + [(8,d) for d in range(1,32)]]
print(len(dates), "target dates")

t0=time.time()
results = {}
def work(d):
    ds_, v, lat, lon = read_slice(d)
    return ds_, v
with ThreadPoolExecutor(max_workers=12) as ex:
    for d,v in ex.map(work, dates):
        results[d]=v
t1=time.time()
print("parallel read of 92 files with 12 workers:", t1-t0, "s")
A = np.stack([results[d] for d in dates], axis=0)
print(A.shape, A.dtype, np.isfinite(A).sum(), "finite of", A.size)
np.save('/tmp/mhw/target.npy', A)
# save coords
lat, lon = read_slice('20080701')[1:3]
np.save('/tmp/mhw/lat.npy', lat); np.save('/tmp/mhw/lon.npy', lon)
print("lat range", lat.min(), lat.max(), "lon range", lon.min(), lon.max())
