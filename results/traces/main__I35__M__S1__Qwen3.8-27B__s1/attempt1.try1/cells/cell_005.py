import h5py, numpy as np, time, os
base = "/data/icsa2027_data_20261101T090944Z/s1z"

t0=time.time()
f = h5py.File(base + "/sst_20090601.nc", "r")
t1=time.time()
sl = f["analysed_sst"][0, 322:382, 485:545][:]
t2=time.time()
lat = f["latitude"][:]; lon = f["longitude"][:]
t3=time.time()
f.close()
print(f"open {t1-t0:.2f}s, slice read {t2-t1:.2f}s, coords {t3-t2:.2f}s")
a = sl.astype(np.float64)
print("finite frac:", np.isfinite(a).mean(), "min/max", np.nanmin(a), np.nanmax(a))
print("Celsius range:", np.nanmin(a)-273.15, np.nanmax(a)-273.15)
