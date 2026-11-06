import xarray as xr, numpy as np, os, time, pickle
base = "/data/icsa2027_data_20261101T090944Z/s1z"
from datetime import date, timedelta

def daterange(d0, d1):
    cur = d0
    while cur <= d1:
        yield cur
        cur += timedelta(days=1)

t0 = time.time()
tgt_files = [f"sst_{d.strftime('%Y%m%d')}.nc" for d in daterange(date(2017,6,1), date(2017,8,31))]
assert all(os.path.exists(os.path.join(base,f)) for f in tgt_files)
T = np.empty((len(tgt_files), 60, 60), dtype="float64")
ds0 = xr.open_dataset(os.path.join(base, tgt_files[0]), engine="h5netcdf")
lat = ds0.latitude.values.astype("float64"); lon = ds0.longitude.values.astype("float64")
slat = (lat>=62.25-1e-9)&(lat<=63.45+1e-9); slon = (lon>=18.73-1e-9)&(lon<=19.93+1e-9)
for i,f in enumerate(tgt_files):
    ds = xr.open_dataset(os.path.join(base,f), engine="h5netcdf")
    T[i] = ds["analysed_sst"].values.astype("float64")[0][slat][:, slon]
    ds.close()
print("target load time", round(time.time()-t0,1), "s", T.shape)
sea = np.isfinite(T).all(axis=0)
print("sea cells:", int(sea.sum()), "of", sea.size)
pickle.dump({"lat":lat, "lon":lon, "slat":slat, "slon":slon, "T":T, "sea":sea}, open("/tmp/target.pkl","wb"))
print("saved /tmp/target.pkl")
