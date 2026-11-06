import h5py, time, numpy as np
base = "/data/icsa2027_data_20261101T090944Z/s1z"
# find lat/lon index ranges from one file
f = h5py.File(f"{base}/sst_20120701.nc", "r")
print(list(f.keys()))
lat = f['latitude'][:]; lon = f['longitude'][:]
li = np.where(np.logical_and(lat >= 60.09, lat <= 61.29))[0]
lo = np.where(np.logical_and(lon >= 20.01, lon <= 21.21))[0]
print(li.min(), li.max(), lo.min(), lo.max())
v = f['analysed_sst']
print("var shape", v.shape, v.dtype, v.chunking, v.compression)
t0 = time.time()
a = v[:, li.min():li.max()+1, lo.min():lo.max()+1][:,0]
print("hyperslab ms:", (time.time()-t0)*1000, a.shape, a.dtype)
t0 = time.time()
a2 = v[0][:]
print("full row ms:", (time.time()-t0)*1000, a2.shape)
f.close()

# compare a few full values
print("hyperslab==full slice:", np.array_equal(a, a2[li.min():li.max()+1, lo.min():lo.max()+1]))
import concurrent.futures, os
print("cpus:", os.cpu_count())
