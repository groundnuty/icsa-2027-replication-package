import fsspec
import os

fs = fsspec.filesystem('onedata')
root_dir = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(root_dir)
# Look for files matching the dataset name
sst_files = [f for f in files if 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m' in f]
print(sst_files)
