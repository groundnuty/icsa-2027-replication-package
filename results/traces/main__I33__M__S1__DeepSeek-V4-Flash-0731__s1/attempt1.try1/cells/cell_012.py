
import time
import h5py
import numpy as np
import os

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# Test loading 10 files in a row
start_time = time.time()
data_list = []
for i in range(10):
    date_str = f'19920{i+1:02d}01' if i < 9 else '19920110'
    # Actually let me just use dates
    from datetime import datetime, timedelta
    d = datetime(1992, 1, 1) + timedelta(days=i)
    date_str = d.strftime('%Y%m%d')
    with h5py.File(f'{data_dir}/sst_{date_str}.nc', 'r') as f:
        sst = f['analysed_sst'][0, 278:338, 613:673]
        data_list.append(sst)
elapsed = time.time() - start_time
print(f"Loading 10 files took {elapsed:.2f} seconds ({elapsed/10:.3f} per file)")
print(f"Total shape: {np.array(data_list).shape}")
