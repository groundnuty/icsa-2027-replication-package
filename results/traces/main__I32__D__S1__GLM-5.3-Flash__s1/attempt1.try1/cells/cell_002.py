import fsspec
fs = fsspec.filesystem('onedata')
entries = fs.ls('icsa2027_data_20261101T090944Z/s1z')
print(len(entries))
print(entries[0])
print(entries[-1])
# check availability of key dates
import re
names = set(e.split('/')[-1] for e in entries)
for d in ['1991-12-27','1991-12-31','1992-01-01','2002-12-31','2003-01-01','2003-01-05','2005-06-01','2005-08-31','2005-02-29','2004-02-29']:
    y,m,dd = d.split('-')
    fn = f'sst_{y}{m}{dd}.nc'
    print(d, fn in names)
