import h5py
import numpy as np

f = h5py.File('/work/sst_s2.nc', 'r')

# Get the analysed_sst dataset
dset = f['analysed_sst']

# Extract baseline: indices 3647:7675, lat 217:277, lon 421:481
# Read in chunks of time
baseline_data = np.zeros((4028, 60, 60), dtype=np.float32)
chunk_size = 100
for start in range(0, 4028, chunk_size):
    end = min(start + chunk_size, 4028)
    baseline_data[start:end] = dset[3647+start:3647+end, 217:277, 421:481]
    print(f"Read baseline chunk {start}-{end}")

print("Baseline shape:", baseline_data.shape)
print("Baseline non-NaN:", np.sum(~np.isnan(baseline_data)))
print("Baseline NaN count:", np.sum(np.isnan(baseline_data)))
