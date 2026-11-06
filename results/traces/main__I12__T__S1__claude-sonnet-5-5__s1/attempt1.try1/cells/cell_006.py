import fsspec
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
for d in ['19920101','20021231','20030105','20090831','19911227','20090601']:
    print(d,fs.exists(f'{p}/sst_{d}.nc'))
try:
    print(len(fs.find(p)))
except Exception as e: print(e)