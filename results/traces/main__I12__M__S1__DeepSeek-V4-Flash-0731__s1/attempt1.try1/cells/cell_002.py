
import os
files = sorted(os.listdir('/data/icsa2027_data_20261101T090944Z/s1z'))
print(len(files))
print(files[:5])
print(files[-5:])
# Check date range of files
import re
dates = [f.replace('sst_','').replace('.nc','') for f in files]
print(dates[0], dates[-1])
