import fsspec
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(path)
# Extract dates from filenames like sst_YYYYMMDD.nc
dates = []
for f in files:
    filename = f.split('/')[-1]
    if filename.startswith('sst_') and filename.endswith('.nc'):
        date_str = filename[4:12]
        dates.append(date_str)

dates.sort()
print(f"First date: {dates[0]}")
print(f"Last date: {dates[-1]}")
print(f"Total files: {len(dates)}")
