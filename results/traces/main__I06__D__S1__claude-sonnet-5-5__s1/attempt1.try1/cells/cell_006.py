import fsspec
fs=fsspec.filesystem('onedata')
for d in ['19911227','19920101','20021231','20120601','20120831','19841001']:
    print(d,fs.exists(f'icsa2027_data_20261101T090944Z/s1z/sst_{d}.nc'))
print(fs.ls.__doc__, [m for m in dir(fs) if not m.startswith('_')][:80])