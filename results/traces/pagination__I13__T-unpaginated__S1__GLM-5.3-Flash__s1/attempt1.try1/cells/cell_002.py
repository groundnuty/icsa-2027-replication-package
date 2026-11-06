import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
lst = fs.ls(base, detail=False)
print('n files:', len(lst))
print('first:', lst[0])
print('last 5:')
for p in lst[-5:]:
    print(p)
# check contiguity of dates
import re, datetime
names = [p.rsplit('/',1)[-1] for p in lst]
dates = []
bad = []
for nm in names:
    m = re.fullmatch(r'sst_(\d{8})\.nc', nm)
    if not m:
        bad.append(nm)
    else:
        dates.append(m.group(1))
print('bad names:', bad[:5], 'count', len(bad))
ds_ = sorted(dates)
print('min', ds_[0], 'max', ds_[-1])
# check for missing dates
d0 = datetime.date(int(ds_[0][:4]), int(ds_[0][4:6]), int(ds_[0][6:]))
d1 = datetime.date(int(ds_[-1][:4]), int(ds_[-1][4:6]), int(ds_[-1][6:]))
alld = []
d = d0
while d <= d1:
    alld.append(d.strftime('%Y%m%d'))
    d += datetime.timedelta(days=1)
missing = sorted(set(alld) - set(ds_))
extra = sorted(set(ds_) - set(alld))
print('missing count:', len(missing), missing[:10])
print('extra count:', len(extra), extra[:10])