import h5py, numpy as np, time, os, datetime as dt

DIR = "/data/icsa2027_data_20261101T090944Z/s1z"
os.makedirs("output", exist_ok=True)
open("output/.persist_test", "w").write("yes")

lat = np.load(os.path.join("output","lat.npy")) if os.path.exists(os.path.join("output","lat.npy")) else None
if lat is None:
    f = h5py.File(DIR + "/sst_20040601.nc", "r")
    lat = f["latitude"][:].copy(); lon = f["longitude"][:].copy(); f.close()
    np.save("output/lat.npy", lat); np.save("output/lon.npy", lon)

lat_sel = (lat >= np.float32(63.31)) & (lat <= np.float32(64.51))
lon_sel = (lon >= np.float32(21.31)) & (lon <= np.float32(22.51))
lat_idx = np.flatnonzero(lat_sel); lon_idx = np.flatnonzero(lon_sel)
np.save("output/lat_idx.npy", lat_idx); np.save("output/lon_idx.npy", lon_idx)

def read_day(d):
    p = f"{DIR}/sst_{d:%Y%m%d}.nc"
    with h5py.File(p, "r") as f:
        v = f["analysed_sst"][0][lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
    return v.astype(np.float32)

t0 = time.time()
for d in [dt.date(1991,12,27), dt.date(1992,6,15), dt.date(2000,2,29), dt.date(2002,12,30), dt.date(2003,1,5)]:
    v = read_day(d)
    assert v.shape == (60, 60), (d, v.shape)
    assert np.isfinite(v).sum() > 0
print("5 reads in %.2f s" % (time.time() - t0))
print("marker exists in this call:", os.path.exists("output/.persist_test"))
print("cwd:", os.getcwd())
