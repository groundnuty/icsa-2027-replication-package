import fsspec
import pandas as pd

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'
all_files = fs.ls(base_path)
sst_files = sorted([f for f in all_files if 'sst_' in f and f.endswith('.nc')])

dates = []
for f in sst_files:
    try:
        date_str = f.split('_')[-1].replace('.nc', '')
        dates.append(pd.to_datetime(date_str))
    except:
        pass

if dates:
    print(f"Date range: {min(dates)} to {max(dates)}")
    print(f"Number of files: {len(dates)}")
else:
    print("No dates found")
