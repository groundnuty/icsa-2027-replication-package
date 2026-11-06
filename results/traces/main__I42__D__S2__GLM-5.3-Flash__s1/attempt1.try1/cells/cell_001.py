import fsspec, os
fs = fsspec.filesystem('onedata')
os.makedirs('/work', exist_ok=True)
try:
    fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', '/work/sst_s2.nc')
    print("downloaded ok")
    print(os.path.getsize('/work/sst_s2.nc'), "bytes")
except Exception as e:
    print("ERR:", type(e).__name__, e)
