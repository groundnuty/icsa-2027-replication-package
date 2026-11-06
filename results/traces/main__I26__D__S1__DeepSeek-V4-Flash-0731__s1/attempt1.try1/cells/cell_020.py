import h5py
import numpy as np

f = h5py.File('/work/sst_s2.nc', 'r')

# Check time attributes
t = f['time']
print("Time attrs:", dict(t.attrs))

# Check the values
vals = t[:10]
print("First 10 time values:", vals)
print("Last 10 time values:", f['time'][-10:])
