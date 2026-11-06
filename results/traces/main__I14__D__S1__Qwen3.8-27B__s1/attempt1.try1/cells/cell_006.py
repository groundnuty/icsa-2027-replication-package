import fsspec, os
os.makedirs('/work/data', exist_ok=True)
fs = fsspec.filesystem('onedata')
# download sample daily file from s1z
fs.get("icsa2027_data_20261101T090944Z/s1z/sst_19920601.nc", "/work/data/sst_19920601.nc") if False else None
# that file doesn't exist in s1z (only 1982-1984); take one that exists
fs.get("icsa2027_data_20261101T090944Z/s1z/sst_19830101.nc", "/work/data/sst_19830101.nc")
print("sample downloaded", os.path.getsize("/work/data/sst_19830101.nc"))