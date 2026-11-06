import fsspec, numpy as np, h5netcdf, time

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
nc = h5netcdf.File(f, 'r')
v = nc['analysed_sst']
h5ds = v._h5ds
print("compression:", h5ds.compression, "opts:", h5ds.compression_opts, "shuffle:", h5ds.shuffle)

t0 = time.time()
slice0 = v[0, 0:20, 0:20]  # small read first
arr = np.asarray(slice0)
print("small read ok:", arr.shape, arr.dtype, "secs:", round(time.time()-t0, 2))
