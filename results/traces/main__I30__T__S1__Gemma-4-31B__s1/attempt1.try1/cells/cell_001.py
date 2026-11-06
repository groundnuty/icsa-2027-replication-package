import fsspec
import os

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(base_path)
# Filter for the dataset name
dataset_files = [f for f in files if 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m' in f]
print(dataset_files)
