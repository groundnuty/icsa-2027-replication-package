import h5py
import numpy as np

f = h5py.File('/work/sst_s2.nc', 'r')

# Check the analysed_sst dataset
dset = f['analysed_sst']
print("Shape:", dset.shape)
print("Dtype:", dset.dtype)
print("Chunks:", dset.chunks if dset.chunks else "not chunked")

# Check dimensions
print("Time:", f['time'].shape, f['time'].dtype)
print("Lat:", f['latitude'].shape)
print("Lon:", f['longitude'].shape)
