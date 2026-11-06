
base='icsa2027_data_20261101T090944Z/s1z/'
for d in ['19910101','19920101','20190601','20190831','20191231','19891231']:
    print(d, fs.exists(base+f'sst_{d}.nc'))
print(sorted(files)[0], sorted(files)[-1])
