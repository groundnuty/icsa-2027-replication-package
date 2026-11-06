import fsspec
fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z/s1z'
names = fs.ls(root, detail=False)
print('n names:', len(names))
names = sorted(names)
print('first:', names[0])
print('last:', names[-1])
# check for gaps in date sequence
import datetime as dt
dates = []
for n in names:
    s = n.split('/')[-1]
    d = s.replace('sst_','').replace('.nc','')
    dates.append(dt.date(int(d[:4]), int(d[4:6]), int(d[6:8])))
dates_sorted = sorted(dates)
print('first date:', dates_sorted[0], 'last:', dates_sorted[-1])
# find gaps
gaps = []
for a, b in zip(dates_sorted, dates_sorted[1:]):
    if (b - a).days != 1:
        gaps.append((a, b, (b-a).days))
print('num gaps:', len(gaps))
for g in gaps[:20]:
    print(g)
