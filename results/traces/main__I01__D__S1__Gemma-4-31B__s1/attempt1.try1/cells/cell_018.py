import fsspec
fs = fsspec.filesystem('onedata')
# Try to find files that might belong to the dataset
# The dataset name is cmems_obs-sst_bal_phy-temp_my_l4_P1D-m
all_files = fs.find('icsa2027_data_20261101T090944Z')
dataset_files = [f for f in all_files if 'cmems' in f or 'sst' in f]
print(f"Total potential files: {len(dataset_files)}")
if dataset_files:
    print(dataset_files[:20])
