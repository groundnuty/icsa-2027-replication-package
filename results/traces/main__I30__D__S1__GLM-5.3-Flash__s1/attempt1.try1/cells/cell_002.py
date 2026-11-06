import fsspec
fs = fsspec.filesystem('onedata')
listing = fs.ls('icsa2027_data_20261101T090944Z/s1z')
print('total files:', len(listing))
print('first:', listing[0])
print('last:', listing[-1])
# check for non .nc or subdirs
import re
weird = [p for p in listing if not re.search(r'sst_\d{8}\.nc$', p.split('/')[-1])]
print('weird entries:', weird[:20])
dates = sorted(p.split('/')[-1][4:12] for p in listing if re.search(r'sst_\d{8}\.nc$', p.split('/')[-1]))
print('date min/max:', dates[0], dates[-1])
print('n unique dates:', len(set(dates)))
