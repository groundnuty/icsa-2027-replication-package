
import os
import numpy as np

# Check saved files
for f in os.listdir('/work'):
    path = os.path.join('/work', f)
    size = os.path.getsize(path)
    print(f"{f}: {size/1e6:.2f} MB")

# Verify data shapes
baseline_sst = np.load('/work/baseline_sst.npy')
target_sst = np.load('/work/target_sst.npy')
print(f"\nbaseline_sst: {baseline_sst.shape}")
print(f"target_sst: {target_sst.shape}")

# Check disk space
stat = os.statvfs('/work')
print(f"\nAvailable disk: {stat.f_bavail * stat.f_frsize / 1e9:.2f} GB")
