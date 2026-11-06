import numpy as np, pickle, os, time
import xarray as xr
base = "/data/icsa2027_data_20261101T090944Z/s1z"
meta = pickle.load(open("/tmp/target.pkl","rb"))
slat, slon = meta["slat"], meta["slon"]
dates = pickle.load(open("/tmp/pools.pkl","rb"))["dates"]
N = len(dates)
Xp = "/tmp/X.npy"
if os.path.exists(Xp):
    X = np.load(Xp)
    print("loaded existing", X.shape)
else:
    X = np.zeros((N, 60, 60), dtype="float64")
print("shape", X.shape, "mem MB:", X.nbytes/1e6)
# chunk 0: files 0..504
CH = 504
i0, i1 = 0, min(CH, N)
t0 = time.time()
for i in range(i0, i1):
    f = f"sst_{dates[i].strftime('%Y%m%d')}.nc"
    ds = xr.open_dataset(os.path.join(base,f), engine="h5netcdf")
    X[i] = ds["analysed_sst"].values.astype("float64")[0][slat][:, slon]
    ds.close()
np.save(Xp, X)
print(f"chunk {i0}-{i1} done in {time.time()-t0:.0f}s")
