import os, json, calendar, datetime as dt
import numpy as np
import xarray as xr

LAT_MIN, LAT_MAX = 54.81, 56.01
LON_MIN, LON_MAX = 19.61, 20.81
T_START = dt.date(2007, 6, 1)
T_END = dt.date(2007, 8, 31)
TOL = 1e-4

import time
ROOT = "/data/icsa2027_data_20261101T090944Z/s1z"
YEARS = list(range(1992, 2003))
NDAYS = 122
FIRST = 5

def read_day(d):
    with xr.open_dataset(f"{ROOT}/sst_{d:%Y%m%d}.nc", engine="h5netcdf") as ds:
        a = ds["analysed_sst"].sel(latitude=slice(LAT_MIN - TOL, LAT_MAX + TOL),
                                   longitude=slice(LON_MIN - TOL, LON_MAX + TOL))
        return a.isel(time=0).values.astype(np.float64), a.latitude.values, a.longitude.values

t0 = time.time()
tdays = [T_START + dt.timedelta(days=i) for i in range((T_END - T_START).days + 1)]

tgt = []
for d in tdays:
    v, lat, lon = read_day(d)
    tgt.append(v)
tgt = np.stack(tgt)
print("target", tgt.shape, round(time.time() - t0, 1), "s")
sea = np.isfinite(tgt).all(axis=0)
sea_idx = np.flatnonzero(sea.ravel())
print("sea cells", len(sea_idx), "of", sea.size)

cube = np.full((len(YEARS), NDAYS, len(lat), len(lon)), np.nan)
for iy, y in enumerate(YEARS):
    for i in range(NDAYS):
        d = dt.date(y, 5, 12) + dt.timedelta(days=FIRST + i)
        cube[iy, i] = read_day(d)[0]
    print(y, "read", round(time.time() - t0, 1), "s")
base = cube.reshape(len(YEARS), NDAYS, -1)[:, :, sea_idx]
print("baseline", base.shape, "NaN share", round(float(np.isnan(base).mean()), 4))

np.save("base_s.npy", base)
np.save("target_s.npy", tgt.reshape(len(tdays), -1)[:, sea_idx])
np.save("sea_idx.npy", sea_idx)
np.save("lat.npy", lat); np.save("lon.npy", lon)
meta = {"years": list(YEARS), "days": [d.isoformat() for d in tdays],
        "baseline_start": dt.date(YEARS[0], 5, 12).isoformat(),
        "baseline_end": dt.date(YEARS[-1], 9, 20).isoformat()}
json.dump(meta, open("meta.json", "w"))
print("saved", base.shape, len(tdays), "days")
