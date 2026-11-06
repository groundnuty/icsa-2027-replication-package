import numpy as np
import h5py

f = h5py.File('/work/sst_s2.nc', 'r')
dset = f['analysed_sst']

# Load baseline and target data
baseline_data = np.zeros((4028, 60, 60), dtype=np.float32)
for start in range(0, 4028, 200):
    end = min(start + 200, 4028)
    baseline_data[start:end] = dset[3647+start:3647+end, 217:277, 421:481]

target_data = dset[9282:9374, 217:277, 421:481].astype(np.float32)

# Save these to disk for later use
np.save('/work/baseline_data.npy', baseline_data)
np.save('/work/target_data.npy', target_data)

print("Data saved")
print("Baseline shape:", baseline_data.shape)
print("Target shape:", target_data.shape)

# Identify sea cells (finite on all target days)
sea_mask = np.all(~np.isnan(target_data), axis=0)
print(f"Sea cells: {np.sum(sea_mask)} out of {sea_mask.size}")
print(f"Sea cell indices:")
for i in range(60):
    for j in range(60):
        if sea_mask[i, j]:
            print(f"  ({i}, {j})", end="")
    if np.any(sea_mask[i, :]):
        pass
print()
