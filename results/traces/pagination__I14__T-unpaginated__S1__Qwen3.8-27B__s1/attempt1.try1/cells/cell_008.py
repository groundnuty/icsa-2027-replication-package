
import fsspec, xarray as xr, numpy as np, time
from concurrent.futures import ThreadPoolExecutor
import datetime as dt, os

os.makedirs('work', exist_ok=True)
fs = fsspec.filesystem('onedata')
BASE = '/icsa2027_data_20261101T090944Z/s1z'

def load_one(name):
    f = fs.open(f'{BASE}/{name}.nc', 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    a = np.asarray(ds['analysed_sst'].values[0])
    lat = ds['latitude'].values; lon = ds['longitude'].values
    ds.close(); f.close()
    return name, a, lat, lon

names = [f"sst_{d.strftime('%Y%m%d')}" for d in [dt.date(2015,6,1)+dt.timedelta(days=i) for i in range(5)]]
t0=time.time()
with ThreadPoolExecutor(max_workers=6) as ex:
    res = list(ex.map(load_one, names))
lat = res[0][2]; lon = res[0][3]
latm = (lat >= 56.13-1e-6) & (lat <= 57.33+1e-6)
lonm = (lon >= 17.71-1e-6) & (lon <= 18.91+1e-6)
sub = np.stack([np.asarray(r[1],dtype=np.float32)[latm][:,lonm] for r in res])
print('batch of 5 done in', time.time()-t0, 's; sub shape', sub.shape)
