
import time
import h5py
import numpy as np

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# Try opening with h5py directly
start_time = time.time()
with h5py.File(f'{data_dir}/sst_19920101.nc', 'r') as f:
    # Check structure
    print("Keys:", list(f.keys()))
    # Try to get the SST data
    for key in f.keys():
        print(f"  {key}: {f[key].shape} {f[key].dtype}")
elapsed = time.time() - start_time
print(f"Open took {elapsed:.2f} seconds")
