import h5py, numpy as np
import fsspec

fs = fsspec.filesystem('onedata')
path = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = fs.open(path, "rb")
with h5py.File(f, "r") as h5:
    def visit(name, obj):
        if isinstance(obj, h5py.Dataset):
            print(name, obj.shape, obj.dtype, "chunks:", obj.chunks, "compression:", obj.compression)
    h5.visititems(visit)
    sst = h5["analysed_sst"]
    print("\nanalysed_sst attrs:", dict(sst.attrs))
    for k in ("units","scale_factor","add_offset","_FillValue","standard_name","long_name"):
        if k in sst.attrs: print(k, "=", sst.attrs[k])
    print("file attrs:", dict(h5.attrs))
