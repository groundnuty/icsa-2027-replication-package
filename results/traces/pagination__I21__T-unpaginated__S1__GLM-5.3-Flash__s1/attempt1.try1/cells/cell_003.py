import fsspec, h5py, numpy as np, time, io
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
p = f'{base}/sst_20210601.nc'

t0=time.time()
f = fs.open(p, 'rb')
hf = h5py.File(f, 'r')
print("keys:", list(hf.keys()))
d = hf['analysed_sst']
print("shape", d.shape, "dtype", d.dtype, "chunks", d.chunks, "compression", d.compression)
lat = hf['latitude'][:]
lon = hf['longitude'][:]
f.close()
print("meta read time %.2fs" % (time.time()-t0))

# locate region indices
lat64 = lat.astype(np.float64); lon64 = lon.astype(np.float64)
lat_sel = np.where((lat64 >= 57.33 - 1e-9) & (lat64 <= 58.53 + 1e-9))[0]
lon_sel = np.where((lon64 >= 9.03 - 1e-9) & (lon64 <= 10.23 + 1e-9))[0]
print("lat idx", lat_sel[0], lat_sel[-1], "n=", len(lat_sel), "vals", lat64[lat_sel[0]], lat64[lat_sel[-1]])
print("lon idx", lon_sel[0], lon_sel[-1], "n=", len(lon_sel), "vals", lon64[lon_sel[0]], lon64[lon_sel[-1]])

t0=time.time()
f = fs.open(p, 'rb')
hf = h5py.File(f, 'r')
sub = hf['analysed_sst'][0, lat_sel[0]:lat_sel[-1]+1, lon_sel[0]:lon_sel[-1]+1]
f.close()
dt = time.time()-t0
print("region read time %.2fs" % dt, sub.shape, sub.dtype, "finite frac", np.isfinite(sub).mean())

# time a full-variable read for comparison
t0=time.time()
f = fs.open(p, 'rb')
hf = h5py.File(f, 'r')
full = hf['analysed_sst'][0]
f.close()
print("full read time %.2fs" % (time.time()-t0))
