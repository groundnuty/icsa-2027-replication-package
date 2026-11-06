import fsspec
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
# Get unique years
years = set()
for f in files:
    name = f.split('/')[-1]
    # sst_YYYYMMDD.nc
    years.add(name[4:8])
print(sorted(years))
print(len(files))
