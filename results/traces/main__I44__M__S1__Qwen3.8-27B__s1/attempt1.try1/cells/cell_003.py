import h5py, numpy as np
p = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20040601.nc"
f = h5py.File(p, "r")
print(f.keys())
for k, v in f.attrs.items():
    print("attr:", k, "=", v)
ds = f["analysed_sst"]
print("shape:", ds.shape, "dtype:", ds.dtype, "chunks:", ds.chunks)
for k, v in ds.attrs.items():
    print("var attr:", k, "=", v)
lat = f["latitude"][:]
lon = f["longitude"][:]
t = f["time"][:]
print("lat dtype", lat.dtype, "lon dtype", lon.dtype)
print("time raw:", t, f["time"].attrs)
# region selection
lat_sel = (lat >= np.float32(63.31)) & (lat <= np.float32(64.51))
lon_sel = (lon >= np.float32(21.31)) & (lon <= np.float32(22.51))
print("n lat:", lat_sel.sum(), lat[lat_sel][:5], lat[lat_sel][-5:])
print("n lon:", lon_sel.sum(), lon[lon_sel][:5], lon[lon_sel][-5:])
# read subarray test
i0 = np.argmax(lat_sel); i1 = len(lat) - np.argmax(lat_sel[::-1])
j0 = np.argmax(lon_sel); j1 = len(lon) - np.argmax(lon_sel[::-1])
sub = ds[0, i0:i1, j0:j1]
print("sub shape", sub.shape, "finite frac:", np.isfinite(sub).mean(), "min/max:", np.nanmin(sub), np.nanmax(sub))
f.close()
