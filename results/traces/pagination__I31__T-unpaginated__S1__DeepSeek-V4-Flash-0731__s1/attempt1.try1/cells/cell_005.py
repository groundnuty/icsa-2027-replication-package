
import fsspec
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')

# Check what years are available
years = set()
for f in files:
    name = f.split('/')[-1]
    # sst_YYYYMMDD.nc
    date_str = name.split('_')[1].split('.')[0]
    years.add(date_str[:4])

print("Years:", sorted(years))
print("Total files:", len(files))
