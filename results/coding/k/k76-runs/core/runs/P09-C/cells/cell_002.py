import os, json, datetime as dt
import numpy as np
import xarray as xr

ROOT = "/data/icsa2027_data_20261101T090944Z"
LAT0, LAT1 = 64.51, 65.71
LON0, LON1 = 21.97, 23.17
T0, T1 = dt.date(2019, 6, 1), dt.date(2019, 8, 31)

def doy(d):
    return dt.date(2000, d.month, d.day).timetuple().tm_yday

def region_slices(lat, lon):
    iy = np.where((lat >= LAT0 - 1e-4) & (lat <= LAT1 + 1e-4))[0]
    ix = np.where((lon >= LON0 - 1e-4) & (lon <= LON1 + 1e-4))[0]
    return slice(int(iy[0]), int(iy[-1]) + 1), slice(int(ix[0]), int(ix[-1]) + 1)

ds = xr.open_dataset(f"{ROOT}/s2z/sst_s2.nc", engine="h5netcdf")
lat_all = ds["latitude"].values
lon_all = ds["longitude"].values
ys, xs = region_slices(lat_all, lon_all)
lat = lat_all[ys]
lon = lon_all[xs]
da = ds["analysed_sst"]
EPOCH = dt.date(1982, 1, 1)

def read_day(d):
    return da.isel(time=(d - EPOCH).days, latitude=ys, longitude=xs).values

def baseline_dates():
    out = []
    for y in range(1992, 2003):
        d = dt.date(y, 5, 12)
        while d <= dt.date(y, 9, 20):
            out.append(d)
            d += dt.timedelta(days=1)
    return out

dates = baseline_dates()
print("baseline days", len(dates))

sst_list = []
for y in range(1992, 2003):
    ds_y = [d for d in dates if d.year == y]
    i0 = (ds_y[0] - EPOCH).days
    i1 = (ds_y[-1] - EPOCH).days
    blk = da.isel(time=slice(i0, i1 + 1), latitude=ys, longitude=xs).values
    sst_list.append(blk)
    print(y, blk.shape)
sst = np.concatenate(sst_list)

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
