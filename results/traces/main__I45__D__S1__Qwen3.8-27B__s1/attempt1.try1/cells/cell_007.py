import fsspec, os, time
import numpy as np
import xarray as xr
import datetime as dt

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/region', exist_ok=True)

def date_list(start, end):
    d = start; out=[]
    while d <= end:
        out.append(d); d += dt.timedelta(days=1)
    return out

base_dates = date_list(dt.date(1991,12,27), dt.date(2003,1,5))
target_dates = date_list(dt.date(2009,6,1), dt.date(2009,8,31))
all_dates = base_dates + target_dates
print("base dates:", len(base_dates), "target dates:", len(target_dates), "total:", len(all_dates))

def region_slice(path):
    ds = xr.open_dataset(path, engine="h5netcdf")
    lat = ds['latitude'].values; lon = ds['longitude'].values
    ls_ = np.where((lat >= 63.31 - 1e-9) & (lat <= 64.51 + 1e-9))[0]
    lo_ = np.where((lon >= 21.31 - 1e-9) & (lon <= 22.51 + 1e-9))[0]
    a = ds['analysed_sst'].isel(time=0).values
    vals = a[ls_[0]:ls_[-1]+1, lo_[0]:lo_[-1]+1].astype(np.float64)
    tval = ds['time'].values[0]
    ds.close()
    return vals, tval

t0 = time.time()
test = all_dates[:40]
miss = []
for d in test:
    fn = f"sst_{d:%Y%m%d}.nc"
    lp = f"/work/region/{fn}"
    rp = f"{base}/{fn}"
    if not os.path.exists(lp):
        try:
            fs.get(rp, lp)
        except Exception as e:
            miss.append((fn, str(e))); continue
    try:
        vals, tval = region_slice(lp)
    except Exception as e:
        miss.append((fn, str(e))); continue
    os.remove(lp)
    np.save(f"/work/region/{d:%Y%m%d}.npy", vals)
dt_ = time.time()-t0
print("processed", len(test), "in", round(dt_,1), "s; missing/errors:", len(miss), miss[:5])
print("est total minutes for 4120:", round(dt_/40*4120/60,1))
