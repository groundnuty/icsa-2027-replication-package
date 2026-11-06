import fsspec
fs=fsspec.filesystem('onedata')
D='icsa2027_data_20261101T090944Z/s1z'
for d in ['19911227','19920101','20021231','20030105','20130601','20130831','19840927']:
    print(d,fs.exists(f'{D}/sst_{d}.nc'))