import fsspec
fs = fsspec.filesystem('onedata')
root_s2z = 'icsa2027_data_20261101T090944Z/s2z'
try:
    files = fs.ls(root_s2z)
    print(f"Files in {root_s2z}:")
    for f in files:
        if 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m' in f:
            print(f)
except Exception as e:
    print(f"Error listing {root_s2z}: {e}")
