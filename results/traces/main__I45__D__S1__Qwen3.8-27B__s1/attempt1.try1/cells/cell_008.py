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

all_dates = date_list(dt.date(1991,12,27), dt.date(2003,1,5)) + date_list(dt.date(2009,6,1), dt.date(2009,8,31))

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
missing = []
done = 0
for i, d in enumerate(all_dates):
    out = f"/work/region/{d:%Y%m%d}.npy"
    if not os.path.exists(out):
        fn = f"sst_{d:%Y%m%d}.nc"
        lp = f"/work/region/{fn}"
        rp = f"{base}/{fn}"
        if not os.path.exists(lp):
            try:
                fs.get(rp, lp)
            except Exception as e:
                missing.append((fn, 'download', str(e)))
                continue
        try:
            vals, tval = region_slice(lp)
        except Exception as e:
            missing.append((fn, 'read', str(e)))
            continue
        os.remove(lp)
        np.save(out, vals)
    done += 1
    if (i+1) % 400 == 0:
        print(f"{i+1}/{len(all_dates)} elapsed {time.time()-t0:.0f}s", flush=True)

print("TOTAL done:", done, "of", len(all_dates), "missing:", len(missing))
for m in missing[:20]:
    print(m)
print("elapsed", round(time.time()-t0,1), "s")
