
import time
import h5py
import numpy as np

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# Try reading just the region data with h5py
start_time = time.time()
with h5py.File(f'{data_dir}/sst_19920101.nc', 'r') as f:
    sst = f['analysed_sst'][0, 278:338, 613:673]
elapsed = time.time() - start_time
print(f"Reading region with h5py took {elapsed:.4f} seconds")
print(f"Shape: {sst.shape}")
print(f"Finite: {np.isfinite(sst).sum()} / {sst.size}")
