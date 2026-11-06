print(x.analysed_sst.attrs)
print(x.attrs['comment'])
base='icsa2027_data_20261101T090944Z/s1z/'
for d in ['19911227','19920101','20030105','20210831','19901231']:
    print(d, fs.exists(base+f'sst_{d}.nc'))