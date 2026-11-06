import h5py
import numpy as np

# Open the NetCDF4 file with h5py
f = h5py.File('/work/sst_s2.nc', 'r')
print("Keys:", list(f.keys()))
