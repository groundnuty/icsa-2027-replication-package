import fsspec, shutil, sys
fs = fsspec.filesystem('onedata')
print("free disk:", shutil.disk_usage('/').free / 1e9, "GB in /")
print("free disk tmp:", shutil.disk_usage('/tmp').free / 1e9, "GB in /tmp")

# Inspect the HDF5 structure for chunking
import h5py
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
with h5py.File(f, 'r') as h:
    print("root keys:", list(h.keys()))
    var = h['analysed_sst']
    print("shape:", var.shape, "dtype:", var.dtype)
    print("chunks:", var.chunks)
    print("compression:", var.compression)
    print("shuffle:", var.shuffle)
    print("fillvalue:", var.fillvalue)
    print("maxshape:", var.maxshape)
    t = h['time']
    print("time shape:", t.shape, "chunks:", t.chunks)
