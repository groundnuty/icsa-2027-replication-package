import fsspec
import os

fs = fsspec.filesystem('onedata')
path_s2z = 'icsa2027_data_20261101T090944Z/s2z'
files_s2z = fs.ls(path_s2z)
dates_s2z = []
for f in files_s2z:
    fname = os.path.basename(f)
    if fname.startswith('sst_') and fname.endswith('.nc'):
        try:
            date_str = fname[4:12]
            dates_s2z.append(date_str)
        except:
            pass

dates_s2z = sorted(dates_s2z)
if dates_s2z:
    print(f"Date range in s2z: {dates_s2z[0]} to {dates_s2z[-1]}")
    print(f"Total files in s2z: {len(dates_s2z)}")
else:
    print("No SST files found in s2z.")
