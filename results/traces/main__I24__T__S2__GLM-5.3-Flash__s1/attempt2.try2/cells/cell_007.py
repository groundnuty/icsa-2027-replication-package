import time, numpy as np, fsspec, h5py

fs = fsspec.filesystem('onedata')
path = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = fs.open(path, "rb")
h5 = h5py.File(f, "r")
sst = h5["analysed_sst"]
tm = h5["time"][:]
print("time raw:", tm[:3], tm.dtype)
lat = h5["latitude"][:]; lon = h5["longitude"][:]
la = lat.astype('float64'); lo = lon.astype('float64')
lat_idx = np.where((la >= 57.57) & (la <= 58.77))[0]
lon_idx = np.where((lo >= 10.25) & (lo <= 11.45))[0]
print("lat_idx:", lat_idx[0], lat_idx[-1], lat_idx.size, "vals", lat[lat_idx[0]], lat[lat_idx[-1]])
print("lon_idx:", lon_idx[0], lon_idx[-1], lon_idx.size, "vals", lon[lon_idx[0]], lon[lon_idx[-1]])

t0 = time.time()
v = sst[12000, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
t1 = time.time()
print("first read:", t1-t0, "s; shape", v.shape, "nNaN", np.isnan(v).sum(), "min/max", np.nanmin(v), np.nanmax(v))

t0 = time.time()
for k in range(10):
    v = sst[12001+k, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
t1 = time.time()
print("10 more reads:", t1-t0, "s ->", (t1-t0)/10, "s/read")
