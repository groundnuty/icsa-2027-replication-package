
import os
import datetime

files = sorted(os.listdir('/data/icsa2027_data_20261101T090944Z/s1z'))

# Check for specific dates
test_dates = ['19911227', '19911231', '19920101', '20021231', '20030101', '20030105', '20090601', '20090831']
for d in test_dates:
    f = f'sst_{d}.nc'
    print(d, f in files)
