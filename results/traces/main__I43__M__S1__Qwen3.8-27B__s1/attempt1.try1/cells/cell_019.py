import numpy as np, pickle, os, time
import xarray as xr
base = "/data/icsa2027_data_20261101T090944Z/s1z"
meta = pickle.load(open("/tmp/target.pkl","rb"))
slat, slon = meta["slat"], meta["slon"]
dates = pickle.load(open("/tmp/pools.pkl","rb"))["dates"]
N = len(dates)
X = np.load("/tmp/X.npy")
CH = 504
for i0 in (CH, 2*CH):
    i1 = min(i0+CH, N)
    t0 = time.time()
    for i in range(i0, i1):
        f = f"sst_{dates[i].strftime('%Y%m%d')}.nc"
        ds = xr.open_dataset(os.path.join(base,f), engine="h5netcdf")
        X[i] = ds["analysed_sst"].values.astype("float64")[0][slat][:, slon]
        ds.close()
    np.save("/tmp/X.npy", X)
    print(f"chunk {i0}-{i1} done in {time.time()-t0:.0f}s")
print("progress", i1, "/", N)
