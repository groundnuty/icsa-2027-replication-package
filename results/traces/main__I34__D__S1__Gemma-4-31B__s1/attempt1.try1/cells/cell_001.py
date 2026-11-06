import fsspec
import os

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(path)
print(f"Found {len(files)} files in {path}")
for f in files:
    if 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m' in f:
        print(f)
