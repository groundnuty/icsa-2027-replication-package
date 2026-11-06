
import fsspec, h5netcdf, time, numpy as np
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
h = h5netcdf.File(f, mode='r')
d = h['analysed_sst']
print([a for a in dir(h) if 'h5' in a.lower() or 'file' in a.lower()])
print([a for a in dir(d) if not a.startswith('__')][:40])
try:
    hf = h._h5py
    print("h5py file:", type(hf))
    dsraw = hf['/analysed_sst']
    print("h5py dataset:", type(dsraw), "chunks:", dsraw.chunks, "shape:", dsraw.shape, "dtype:", dsraw.dtype)
    print("fillvalue:", dsraw.fillvalue)
except Exception as e:
    print("err:", e)
t0 = time.time()
x = d[1000, 48:108, 353:413]
print("1-day 60x60 read: %.2fs, shape %s, finite %.3f, nan %d, range %.2f..%.2f" % (
    time.time()-t0, x.shape, float(np.isfinite(x).mean()), int(np.isnan(x).sum()), float(np.nanmin(x)), float(np.nanmax(x))))
h.close(); f.close()
