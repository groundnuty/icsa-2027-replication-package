import fsspec
fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'
# List all files recursively to find the dataset
all_files = fs.find(base_path)
sst_files = [f for f in all_files if 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m' in f]
print(sst_files)
