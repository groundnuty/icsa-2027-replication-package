import os, json
os.makedirs('/work/cache', exist_ok=True)

script = r'''
import fsspec, xarray as xr, numpy as np, json, time, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

LAT0, LAT1 = 57.83, 59.03
LON0, LON1 = 17.41, 18.61

def daterange(a, b):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)

base_dates = list(daterange(date(1991,12,27), date(2003,1,5)))
tgt_dates  = list(daterange(date(2007,6,1), date(2007,8,31)))
all_dates = base_dates + tgt_dates
print("n base days:", len(base_dates), "n tgt days:", len(tgt_dates))

def read_one(d, latidx, lonidx):
    p = base + f"/sst_{d.year}{d.month:02d}{d.day:02d}.nc"
    last_err = None
    for attempt in range(4):
        try:
            f = fs.open(p, "rb")
            ds = xr.open_dataset(f, engine="h5netcdf")
            v = ds['analysed_sst'].isel(latitude=latidx, longitude=lonidx).values[0]
            f.close()
            return d, v.astype(np.float32)
        except Exception as e:
            last_err = e
            time.sleep(1 + attempt*2)
    raise RuntimeError(f"failed {p}: {last_err}")

# determine index slices from first file
f = fs.open(base + "/sst_19920101.nc", "rb")
ds = xr.open_dataset(f, engine="h5netcdf")
lat = ds.latitude.values.copy()
lon = ds.longitude.values.copy()
f.close()
latidx = np.where((lat >= LAT0-1e-9) & (lat <= LAT1+1e-9))[0]
lonidx = np.where((lon >= LON0-1e-9) & (lon <= LON1+1e-9))[0]
print("lat slice:", lat[latidx[0]], lat[latidx[-1]], "lon slice:", lon[lonidx[0]], lon[lonidx[-1]])
print("nlat:", latidx.size, "nlon:", lonidx.size)

A_base = np.full((len(base_dates), latidx.size, lonidx.size), np.nan, dtype=np.float32)
A_tgt  = np.full((len(tgt_dates),  latidx.size, lonidx.size), np.nan, dtype=np.float32)

t0 = time.time()
done = 0
with ThreadPoolExecutor(max_workers=12) as ex:
    futs = []
    for i, d in enumerate(base_dates):
        futs.append((i, 'b', ex.submit(read_one, d, latidx, lonidx)))
    for i, d in enumerate(tgt_dates):
        futs.append((i, 't', ex.submit(read_one, d, latidx, lonidx)))
    for i, tag, fut in futs:
        d, v = fut.result()
        if tag == 'b':
            A_base[i] = v
        else:
            A_tgt[i] = v
        done += 1
        if done % 400 == 0:
            print(f"{done}/{len(futs)} files, {time.time()-t0:.0f}s", flush=True)

np.savez_compressed('/work/cache/data.npz',
                    A_base=A_base, A_tgt=A_tgt, lat=lat[latidx], lon=lon[lonidx])
json.dump({"base": [d.isoformat() for d in base_dates], "tgt": [d.isoformat() for d in tgt_dates]},
          open('/work/cache/dates.json', 'w'))
print("TOTAL:", time.time()-t0, "s")
print("base nan per day (min,max):", np.nanmin(~np.isfinite(A_base).sum(axis=(1,2))), np.nanmax(~np.isfinite(A_base).sum(axis=(1,2))))
print("tgt  nan per day (min,max):", np.nanmin(~np.isfinite(A_tgt).sum(axis=(1,2))), np.nanmax(~np.isfinite(A_tgt).sum(axis=(1,2))))
'''
open('/work/mhw_load.py', 'w').write(script)
print("written")
