
import fsspec, xarray as xr, numpy as np, time, os, datetime, json

os.makedirs("/tmp/mhw", exist_ok=True)
os.makedirs("output", exist_ok=True)
fs = fsspec.filesystem('onedata')
BASE = "icsa2027_data_20261101T090944Z/s1z"

def read_day(date):
    path = f"{BASE}/sst_{date.strftime('%Y%m%d')}.nc"
    with fs.open(path, "rb") as f:
        ds = xr.open_dataset(f, engine="h5netcdf")
        v = ds["analysed_sst"].values[:, 322:382, 485:545].astype(np.float64)
        ds.close()
    return v[0]  # (60, 60)

# verify index slice matches region exactly on one file
f = fs.open(f"{BASE}/sst_20070601.nc", "rb")
ds = xr.open_dataset(f, engine="h5netcdf")
lat = ds["latitude"].values; lon = ds["longitude"].values
eps = 1e-6
lat_sel = np.where((lat >= 59.93 - eps) & (lat <= 61.13 + eps))[0]
lon_sel = np.where((lon >= 18.69 - eps) & (lon <= 19.89 + eps))[0]
assert (lat_sel == np.arange(322, 382)).all() and (lon_sel == np.arange(485, 545)).all(), (lat_sel[:3], lat_sel[-3:], lon_sel[:3], lon_sel[-3:])
np.save("/tmp/mhw/lat.npy", lat[lat_sel]); np.save("/tmp/mhw/lon.npy", lon[lon_sel])
ds.close()
print("coords saved:", lat[lat_sel[0]], "->", lat[lat_sel[-1]], "|", lon[lon_sel[0]], "->", lon[lon_sel[-1]])

d0 = datetime.date(2007, 6, 1)
d1 = datetime.date(2007, 8, 31)
ndays = (d1 - d0).days + 1
print("target days:", ndays)
t0 = time.time()
arr = np.empty((ndays, 60, 60), dtype=np.float64)
for i in range(ndays):
    d = d0 + datetime.timedelta(days=i)
    arr[i] = read_day(d)
    if i % 20 == 0:
        print(i, d, "elapsed", round(time.time()-t0, 1), "s", flush=True)
np.save("/tmp/mhw/target.npy", arr)
np.save("/tmp/mhw/target_dates.npy", np.array([ (d0+datetime.timedelta(days=i)).toordinal() for i in range(ndays) ]))
finite_all = np.isfinite(arr).all(axis=0)
print("sea cells:", int(finite_all.sum()), "of 3600")
np.save("/tmp/mhw/sea_cells.npy", finite_all)
print("total elapsed:", round(time.time()-t0, 1), "s")
