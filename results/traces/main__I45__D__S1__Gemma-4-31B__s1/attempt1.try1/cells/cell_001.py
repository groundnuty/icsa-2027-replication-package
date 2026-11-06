import fsspec
import os

fs = fsspec.filesystem('onedata')
remote_dir = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(remote_dir)
# Filter for the specific dataset
dataset_name = 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m'
relevant_files = [f for f in files if dataset_name in f]
print(f"Found {len(relevant_files)} files matching the dataset name.")
for f in sorted(relevant_files)[:10]:
    print(f)
if len(relevant_files) > 10:
    print("...")
