import fsspec, re, json, time
fs = fsspec.filesystem('onedata')
client = fs.client
names = []
token = None
t0 = time.time()
for page in range(200):
    res = client.list_children('icsa2027_data_20261101T090944Z', file_path='s1z', limit=1000, continuation_token=token)
    for ch in res['children']:
        names.append(ch['name'])
    token = res.get('nextPageToken')
    if res.get('isLast', True) or token is None:
        break
print('pages done in', round(time.time()-t0,1), 's; total files:', len(names))
dates = sorted(set(re.findall(r'sst_(\d{8})\.nc', '\n'.join(names))))
print('unique date files:', len(dates))
print('first:', dates[0], 'last:', dates[-1])
# Check for missing days between first and last
from datetime import date, timedelta
d0 = date(int(dates[0][:4]), int(dates[0][4:6]), int(dates[0][6:]))
d1 = date(int(dates[-1][:4]), int(dates[-1][4:6]), int(dates[-1][6:]))
missing = []
d = d0
ds = set(dates)
while d <= d1:
    if d.strftime('%Y%m%d') not in ds:
        missing.append(d.isoformat())
    d += timedelta(days=1)
print('missing days in range:', len(missing), missing[:20])
# non-sst files
other = [n for n in names if not re.match(r'.*sst_\d{8}\.nc$', n)]
print('other files:', other[:10], 'count:', len(other))
# save the list locally
with open('/work/filelist.json','w') as f:
    json.dump(names, f)
