import fsspec, time, os, datetime as dt
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z'
# test batch get including a nonexistent file
os.makedirs('/work/dl3', exist_ok=True)
names = [p + '/sst_19920601.nc', p + '/sst_19920602.nc', p + '/sst_99990101.nc', p + '/sst_19920603.nc']
try:
    fs.get(names, '/work/dl3/')
    print('batch ok')
except Exception as ex:
    print('batch err:', type(ex).__name__, str(ex)[:300])
print(sorted(os.listdir('/work/dl3')))
