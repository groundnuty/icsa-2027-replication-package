import fsspec
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
for n in ['20030601','20030831','19920101','20021231','19911227','20030105']:
    print(n,fs.exists(f'{p}/sst_{n}.nc'))