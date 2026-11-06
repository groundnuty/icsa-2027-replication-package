import h5py
import numpy as np

f = h5py.File('/work/sst_s2.nc', 'r')
dset = f['analysed_sst']

# Extract target: indices 9282:9374, lat 217:277, lon 421:481
target_data = dset[9282:9374, 217:277, 421:481]
print("Target shape:", target_data.shape)
print("Target dtype:", target_data.dtype)
print("Target non-NaN:", np.sum(~np.isnan(target_data)))
print("Target NaN count:", np.sum(np.isnan(target_data)))
