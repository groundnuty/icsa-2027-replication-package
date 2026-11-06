import os, json, datetime as dt
import numpy as np
import xarray as xr

ROOT = "/data/icsa2027_data_20261101T090944Z"
LAT0, LAT1 = 57.33, 58.53
LON0, LON1 = 9.03, 10.23
T0, T1 = dt.date(2012, 6, 1), dt.date(2012, 8, 31)

def doy(d):
    return dt.date(2000, d.month, d.day).timetuple().tm_yday

def region_slices(lat, lon):
    iy = np.where((lat >= LAT0 - 1e-4) & (lat <= LAT1 + 1e-4))[0]
    ix = np.where((lon >= LON0 - 1e-4) & (lon <= LON1 + 1e-4))[0]
    return slice(int(iy[0]), int(iy[-1]) + 1), slice(int(ix[0]), int(ix[-1]) + 1)

ds0 = xr.open_dataset(f"{ROOT}/s1z/sst_{T0:%Y%m%d}.nc", engine="h5netcdf")
lat_all = ds0["latitude"].values
lon_all = ds0["longitude"].values
ds0.close()
ys, xs = region_slices(lat_all, lon_all)
lat = lat_all[ys]
lon = lon_all[xs]

def read_day(d):
    with xr.open_dataset(f"{ROOT}/s1z/sst_{d:%Y%m%d}.nc", engine="h5netcdf") as ds:
        return ds["analysed_sst"].isel(time=0, latitude=ys, longitude=xs).values

def baseline_dates():
    out = []
    for y in range(1992, 2003):
        d0 = dt.date(y, 5, 12)
        for k in range(132):
            out.append(d0 + dt.timedelta(days=k - (1 if k == 50 else 0)))
    return out

dates = baseline_dates()
print("baseline days", len(dates), "per year", len(dates) // 11)

sst_list = []
for n, d in enumerate(dates):
    sst_list.append(read_day(d))
    if (n + 1) % 150 == 0:
        print("loaded", n + 1, "of", len(dates), d)
sst = np.stack(sst_list)

print("baseline", sst.shape, dates[0], dates[-1])
np.save("base_sst.npy", sst)
np.save("base_dates.npy", np.array([int(f"{d:%Y%m%d}") for d in dates]))

tdates = [T0 + dt.timedelta(days=k) for k in range((T1 - T0).days + 1)]
tgt = np.stack([read_day(d) for d in tdates])
print("target", tgt.shape, tdates[0], tdates[-1])
sea = np.isfinite(tgt).all(axis=0)
print("sea cells", int(sea.sum()), "of", sea.size)
np.save("tgt_sst.npy", tgt)
np.save("tgt_dates.npy", np.array([int(f"{d:%Y%m%d}") for d in tdates]))
np.save("lat.npy", lat)
np.save("lon.npy", lon)
