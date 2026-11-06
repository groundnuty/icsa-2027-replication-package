import fsspec
import os

fs = fsspec.filesystem('onedata')
remote_dir = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(remote_dir)
print(f"Total files in {remote_dir}: {len(files)}")
# Filter for the specific dataset pattern
sst_files = [f for f in files if 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m' in f]
print(f"SST files: {len(sst_files)}")
for f in sst_files[:10]:
    print(f)
