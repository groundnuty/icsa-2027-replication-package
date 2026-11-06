
import fsspec, xarray as xr, numpy as np, time, datetime

fs = fsspec.filesystem('onedata')
BASE = "icsa2027_data_20261101T090944Z/s1z"
sea = np.load("/tmp/mhw/sea_cells.npy")
sea_idx = np.argwhere(sea)
print("sea cells:", len(sea_idx))

def read_day_cells(date, idx):
    path = f"{BASE}/sst_{date.strftime('%Y%m%d')}.nc"
    with fs.open(path, "rb") as f:
        ds = xr.open_dataset(f, engine="h5netcdf")
        v = ds["analysed_sst"].values[0][322:382, 485:545].astype(np.float64)
        ds.close()
    return v[idx[:, 0], idx[:, 1]]

d0 = datetime.date(1991, 12, 27)
d1 = datetime.date(2003, 1, 5)
ndays = (d1 - d0).days + 1
print("baseline+margin days:", ndays)
t0 = time.time()
arr = np.empty((ndays, len(sea_idx)), dtype=np.float64)
for i in range(ndays):
    d = d0 + datetime.timedelta(days=i)
    arr[i] = read_day_cells(d, sea_idx)
    if i % 500 == 0:
        print(i, d, "elapsed", round(time.time()-t0, 1), "s", flush=True)
np.save("/tmp/mhw/baseline.npy", arr)
np.save("/tmp/mhw/baseline_dates.npy", np.array([(d0+datetime.timedelta(days=i)).toordinal() for i in range(ndays)]))
print("NaNs per cell:", int(np.isnan(arr).sum()), "of", arr.size)
print("total elapsed:", round(time.time()-t0, 1), "s")
