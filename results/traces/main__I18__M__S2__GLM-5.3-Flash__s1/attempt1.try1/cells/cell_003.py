import xarray as xr, numpy as np, h5py
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
with h5py.File(path, "r") as f:
    def show(name, obj):
        if isinstance(obj, h5py.Dataset):
            print(name, obj.shape, obj.dtype, "chunks:", obj.chunks, "compression:", obj.compression)
    f.visititems(show)
    print("--- attrs of analysed_sst ---")
    for k,v in f["analysed_sst"].attrs.items():
        print(k, v)
