import fsspec,datetime as dt
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
for s in ['19920101','20021231','20030105','20190601','20190831','19911227','19840927']:
    print(s,fs.exists(f'{p}/sst_{s}.nc'))
print(len(fs.find(p)))