import h5py, numpy as np, time as tm
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = h5py.File(path, "r")
tt = f["time"][:]
# decode: seconds since 1981-01-01
import datetime as dt
epoch = np.datetime64("1981-01-01")
times = epoch + tt.astype("timedelta64[s]")
print(times[0], times[-1], len(times))

def idx_range(a, b):
    i0 = np.searchsorted(times, np.datetime64(a)); i1 = np.searchsorted(times, np.datetime64(b), side="right")
    return i0, i1

# check continuity of dates in baseline span
i0, i1 = idx_range("1991-12-27", "2003-01-05")
print("baseline span idx:", i0, i1, "n:", i1-i0)
d0, d1 = times[i0], times[i1-1]
ndays = (d1 - d0).astype(int) + 1
print("calendar span days:", ndays, "matches:", ndays == i1-i0)

i0t, i1t = idx_range("2010-06-01", "2010-08-31")
print("target idx:", i0t, i1t, "n:", i1t-i0t, times[i0t], times[i1t-1])

lat = f["latitude"][:]; lon = f["longitude"][:]
i = np.searchsorted(lat, 57.13, side="left"); j = np.searchsorted(lat, 58.33, side="right")
k = np.searchsorted(lon, 22.79, side="left"); l = np.searchsorted(lon, 23.99, side="right")

t0 = tm.time()
base = f["analysed_sst"][i0:i1, i:j, k:l].astype(np.float64)
print("base read:", tm.time()-t0, base.shape)
t0 = tm.time()
tgt = f["analysed_sst"][i0t:i1t, i:j, k:l].astype(np.float64)
print("tgt read:", tm.time()-t0, tgt.shape)
f.close()

np.save("/tmp/base.npy", base)
np.save("/tmp/tgt.npy", tgt)
np.save("/tmp/base_times.npy", times[i0:i1].astype("datetime64[D]").astype(int))
np.save("/tmp/tgt_times.npy", times[i0t:i1t].astype("datetime64[D]").astype(int))
np.save("/tmp/latlon.npy", np.concatenate([lat[i:j], lon[k:l]]))
print("finite frac base:", np.isfinite(base).mean(), "tgt:", np.isfinite(tgt).mean())
