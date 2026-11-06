
import fsspec, h5netcdf, time, numpy as np
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
h = h5netcdf.File(f, mode='r')
d = h['analysed_sst']
print("shape:", d.shape, "dtype:", d.dtype)
print("chunksizes:", d.chunksizes)
print("dims order:", list(d.dimensions.keys()) if hasattr(d.dimensions,'keys') else d.dimensions)
print("attrs:", dict(d._attributes) if hasattr(d, '_attributes') else d.attributes)
t = h['time']
print("time shape:", t.shape, t.dtype)
# timing probes: one day, 60x60 block
lat0, lat1, lon0, lon1 = 48, 108, 353, 413
t0 = time.time()
x = d[1000, lat0:lat1, lon0:lon1]
dt1 = time.time() - t0
print("1-day 60x60 read: %.2fs, shape %s, finite frac %.3f, nan %d" % (dt1, x.shape, np.isfinite(x).mean(), int(np.isnan(x).sum())))
t0 = time.time()
y = d[1000:1030, lat0:lat1, lon0:lon1]
dt2 = time.time() - t0
print("30-day 60x60 read: %.2fs, shape %s" % (dt2, y.shape))
h.close(); f.close()
