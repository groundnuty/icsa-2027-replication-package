import os
import glob

dataset_dir = '/data/icsa2027_data_20261101T090944Z/s1z'
files = sorted(glob.glob(os.path.join(dataset_dir, 'sst_*.nc')))
print(f"First file: {files[0]}")
print(f"Last file: {files[-1]}")
print(f"Total files: {len(files)}")
