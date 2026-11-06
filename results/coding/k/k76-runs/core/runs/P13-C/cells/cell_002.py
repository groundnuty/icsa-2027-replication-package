import os, json, datetime as dt
import numpy as np
import xarray as xr

ROOT = "/data/icsa2027_data_20261101T090944Z"
LAT0, LAT1 = 60.09, 61.29
LON0, LON1 = 20.01, 21.21
T0, T1 = dt.date(2003, 6, 1), dt.date(2003, 8, 31)

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

tdates = [T0 + dt.timedelta(days=k) for k in range((T1 - T0).days + 1)]
tgt = np.stack([read_day(d) for d in tdates])
print("target", tgt.shape, tdates[0], tdates[-1])
sea = np.isfinite(tgt).all(axis=0)
print("sea cells", int(sea.sum()), "of", sea.size)
np.save("tgt_sst.npy", tgt)
np.save("tgt_dates.npy", np.array([int(f"{d:%Y%m%d}") for d in tdates]))
np.save("lat.npy", lat)
np.save("lon.npy", lon)

nrow = sea.shape[0]
nblk = 4
step = nrow // nblk
print("row blocks", nblk, "of", step, "rows")
for b in range(nblk):
    r0, r1 = b * step, (b + 1) * step
    rows = slice(ys.start + r0, ys.start + r1)
    parts, dd = [], []
    for y in range(1992, 2003):
        lo = (dt.date(y, 5, 12) - EPOCH).days
        hi = (dt.date(y, 9, 20) - EPOCH).days
        parts.append(da.isel(time=slice(lo, hi + 1), latitude=rows, longitude=xs).values)
        dd += [int((EPOCH + dt.timedelta(days=int(n))).strftime("%Y%m%d")) for n in range(lo, hi + 1)]
    blk = np.concatenate(parts)
    np.save(f"blk{b}_sst.npy", blk)
    np.save(f"blk{b}_dates.npy", np.array(dd))
    print("block", b, "rows", r0, r1, blk.shape)
