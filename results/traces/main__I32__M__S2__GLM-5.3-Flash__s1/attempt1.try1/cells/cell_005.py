import xarray as xr, numpy as np, time
p = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(p, engine="h5netcdf")
t = ds.time.values
lat = ds.latitude.values; lon = ds.longitude.values
la = np.where((lat >= 59.05-1e-6) & (lat <= 60.25+1e-6))[0]
lo = np.where((lon >= 21.25-1e-6) & (lon <= 22.45+1e-6))[0]
i0, i1 = la[0], la[-1]; j0, j1 = lo[0], lo[-1]

ts = t.astype('datetime64[D]').astype(int)  # days since epoch
tdate = t.astype('datetime64[D]')
def yr_slice(y): return slice(f"{y}-01-01", f"{y}-12-31")

t00 = time.time()
data = {}  # year -> array (ndays, 60, 60) float64
for y in list(range(1991, 2004)) + [2005]:
    m = (tdate >= np.datetime64(f"{y}-01-01")) & (tdate <= np.datetime64(f"{y}-12-31"))
    idx = np.where(m)[0]
    arr = np.empty((idx.size, 60, 60), dtype=np.float64)
    for k, ti in enumerate(idx):
        arr[k] = ds.analysed_sst.isel(time=ti, latitude=slice(i0, i1+1), longitude=slice(j0, j1+1)).values.astype(np.float64)
    data[y] = arr
    print(y, arr.shape, "finite frac %.4f" % np.isfinite(arr).mean())
print("total read time %.1fs" % (time.time()-t00))
np.save("/data_out_tmp.npy", np.concatenate([data[y] for y in sorted(data)], axis=0)) if False else None
import pickle
with open("/tmp/data.pkl","wb") as f:
    pickle.dump({"data": data, "ts": ts, "i0": i0, "i1": i1, "j0": j0, "j1": j1}, f, protocol=4)
print("saved pickle")
