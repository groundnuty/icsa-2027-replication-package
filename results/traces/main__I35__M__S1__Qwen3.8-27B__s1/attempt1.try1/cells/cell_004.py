import h5py
base = "/data/icsa2027_data_20261101T090944Z/s1z"
f = h5py.File(base + "/sst_20090601.nc", "r")
print(list(f.keys()))
v = f["analysed_sst"]
print("shape", v.shape, "dtype", v.dtype)
for k, val in v.attrs.items():
    print("attr", k, "=", val)
# latitude slice indices for region
import numpy as np
lat = f["latitude"][:]
lon = f["longitude"][:]
print("lat min/max", lat.min(), lat.max(), "lon min/max", lon.min(), lon.max())
i0 = np.searchsorted(lat, 59.93, side="left"); i1 = np.searchsorted(lat, 61.13, side="right")
j0 = np.searchsorted(lon, 18.69, side="left"); j1 = np.searchsorted(lon, 19.89, side="right")
print("lat idx", i0, i1, lat[i0:i1:5])
print("lon idx", j0, j1, lon[j0:j1:5])
sl = v[0, i0:i1, j0:j1]
arr = sl[...]
print("raw slice sample", arr[:2,:2], arr.dtype)
f.close()
