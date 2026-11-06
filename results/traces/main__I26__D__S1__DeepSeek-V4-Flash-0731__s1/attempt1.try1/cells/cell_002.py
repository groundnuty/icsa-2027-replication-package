import fsspec
fs = fsspec.filesystem('onedata')
# List all files to understand what years are available
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
print(len(files))
# Get unique years
years = set()
for f in files:
    name = f.split('/')[-1]
    year = name[4:8]
    years.add(year)
print(sorted(years))
