import os, json, calendar, datetime as dt
import numpy as np
import xarray as xr

LAT_MIN, LAT_MAX = 54.81, 56.01
LON_MIN, LON_MAX = 19.61, 20.81
T_START = dt.date(2007, 6, 1)
T_END = dt.date(2007, 8, 31)
TOL = 1e-4

import time
P = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
YEARS = list(range(1992, 2003))
NDAYS = 132
FIRST = 0
T0 = dt.date(1982, 1, 1)

ds = xr.open_dataset(P, engine="h5netcdf")
lat = ds.latitude.values; lon = ds.longitude.values
la = np.flatnonzero((lat >= LAT_MIN - TOL) & (lat <= LAT_MAX + TOL))
lo = np.flatnonzero((lon >= LON_MIN - TOL) & (lon <= LON_MAX + TOL))
sst = ds["analysed_sst"].isel(latitude=slice(la[0], la[-1] + 1), longitude=slice(lo[0], lo[-1] + 1))
lat = lat[la]; lon = lon[lo]

def read_span(d0, d1):
    return sst.isel(time=slice((d0 - T0).days, (d1 - T0).days + 1)).values.astype(np.float64)

t0 = time.time()
tdays = [T_START + dt.timedelta(days=i) for i in range((T_END - T_START).days + 1)]

tgt = read_span(tdays[0], tdays[-1])
print("target", tgt.shape, round(time.time() - t0, 1), "s")
sea = np.isfinite(tgt).all(axis=0)
sea_idx = np.flatnonzero(sea.ravel())
print("sea cells", len(sea_idx), "of", sea.size)

cube = np.full((len(YEARS), NDAYS, len(lat), len(lon)), np.nan)
for iy, y in enumerate(YEARS):
    d0 = dt.date(y, 5, 12) + dt.timedelta(days=FIRST)
    cube[iy] = read_span(d0, d0 + dt.timedelta(days=NDAYS - 1))
    print(y, "read", round(time.time() - t0, 1), "s")
base = cube.reshape(len(YEARS), NDAYS, -1)[:, :, sea_idx]
print("baseline", base.shape, "NaN share", round(float(np.isnan(base).mean()), 4))

np.save("cube.npy", cube)
np.save("target.npy", tgt)
np.save("lat.npy", lat); np.save("lon.npy", lon)
meta = {"years": list(YEARS), "days": [d.isoformat() for d in tdays],
        "baseline_start": dt.date(YEARS[0], 5, 12).isoformat(),
        "baseline_end": dt.date(YEARS[-1], 9, 20).isoformat()}
json.dump(meta, open("meta.json", "w"))
print("saved", cube.shape, tgt.shape)
