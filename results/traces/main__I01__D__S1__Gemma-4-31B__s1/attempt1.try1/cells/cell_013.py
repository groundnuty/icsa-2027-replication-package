import fsspec
fs = fsspec.filesystem('onedata')
# Try to find any directory containing the dataset name
all_dirs = fs.find('')
dataset_name = 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m'
matching_dirs = [d for d in all_dirs if dataset_name in d]
print(f"Matching directories: {matching_dirs}")
