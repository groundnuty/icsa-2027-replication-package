
import fsspec, xarray as xr, numpy as np, time
from concurrent.futures import ThreadPoolExecutor
import datetime as dt, os, pickle

os.makedirs('work', exist_ok=True)
fs = fsspec.filesystem('onedata')
BASE = '/icsa2027_data_20261101T090944Z/s1z'

def daterange(a, b):
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)

base_days  = list(daterange(dt.date(1991,12,27), dt.date(2003,1,5)))   # 4041
target_days = list(daterange(dt.date(2015,6,1), dt.date(2015,8,31)))    # 92
print(len(base_days), len(target_days))

def load_one(d):
    name = f"sst_{d.strftime('%Y%m%d')}"
    f = fs.open(f'{BASE}/{name}.nc', 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    a = np.ascontiguousarray(ds['analysed_sst'].values[0], dtype=np.float32)
    lat = ds['latitude'].values; lon = ds['longitude'].values
    ds.close(); f.close()
    latm = (lat >= 56.13-1e-6) & (lat <= 57.33+1e-6)
    lonm = (lon >= 17.71-1e-6) & (lon <= 18.91+1e-6)
    return d, a[latm][:, lonm], lat[latm], lon[lonm]

t0 = time.time()
with ThreadPoolExecutor(max_workers=8) as ex:
    res = list(ex.map(load_one, base_days + target_days))
res.sort(key=lambda r: r[0])
all_days = [r[0] for r in res]
sst = np.stack([r[1] for r in res]).astype(np.float64)
lat = res[0][2].astype(np.float64); lon = res[0][3].astype(np.float64)
print('loaded in', round(time.time()-t0,1), 's; sst', sst.shape, sst.dtype)
np.savez_compressed('work/sst.npz', days=np.array([d.strftime('%Y-%m-%d') for d in all_days]), sst=sst, lat=lat, lon=lon)
# sanity: finite fraction per day
frac = np.isfinite(sst).mean(axis=(1,2))
print('finite frac min/mean/max:', frac.min().round(3), frac.mean().round(3), frac.max().round(3))
np.save('work/lat.npy', lat); np.save('work/lon.npy', lon)
print('lat first/last', lat[0], lat[-1], 'lon first/last', lon[0], lon[-1])
