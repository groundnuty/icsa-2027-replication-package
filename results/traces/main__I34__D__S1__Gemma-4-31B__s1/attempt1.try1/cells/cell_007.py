import fsspec
fs = fsspec.filesystem('onedata')
path_s2z = 'icsa2027_data_20261101T090944Z/s2z'
files_s2z = fs.ls(path_s2z)
dates_s2z = sorted([f.split('/')[-1][4:12] for f in files_s2z if f.split('/')[-1].startswith('sst_')])
print(f"s2z first date: {dates_s2z[0]}")
print(f"s2z last date: {dates_s2z[-1]}")
print(f"s2z total files: {len(dates_s2z)}")
