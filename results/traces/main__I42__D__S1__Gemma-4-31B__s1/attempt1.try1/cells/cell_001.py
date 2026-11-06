import fsspec
fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(root)
print(f"Files in {root}:")
for f in files:
    if 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m' in f:
        print(f)
