from onedatarestfsspec.core import OnedataFileRESTClient
import fsspec
fs = fsspec.filesystem('onedata')
client = fs.client
space = 'icsa2027_data_20261101T090944Z'
all_names = []
token = None
while True:
    res = client.list_children(space, file_path='s1z', attributes=["name","type"], limit=1000, continuation_token=token)
    for ch in res["children"]:
        all_names.append(ch["name"])
    token = res.get("nextPageToken")
    if res.get("isLast", True) or token is None:
        break
print("total files:", len(all_names))
print("first:", all_names[0], "last:", all_names[-1])
import re, datetime as dt
pat = re.compile(r'^sst_(\d{8})\.nc$')
dates = []
for n in all_names:
    m = pat.match(n)
    if m: dates.append(dt.datetime.strptime(m.group(1), "%Y%m%d").date())
dates = sorted(dates)
print("sst files:", len(dates), "range:", dates[0], dates[-1])
# save listing
with open('/work/filelist.txt','w') as f:
    for n in all_names:
        f.write(n+"\n")
# check needed dates present
need = set()
cur = dt.date(1991,12,26)
while cur <= dt.date(2003,1,6): need.add(cur); cur += dt.timedelta(days=1)
cur = dt.date(2012,5,30)
while cur <= dt.date(2012,9,2): need.add(cur); cur += dt.timedelta(days=1)
present = set(dates)
miss = sorted(need - present)
print("missing needed:", miss, len(miss))
print("other non-sst files:", [n for n in all_names if not pat.match(n)])
