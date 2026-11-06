import fsspec
fs = fsspec.filesystem('onedata')
base = "icsa2027_data_20261101T090944Z/s1z"
names = [f['name'].split('/')[-1] for f in fs.ls(base, detail=True)]
print("total files:", len(names))
print("first:", names[:3])
print("last:", names[-3:])
# check which of the files we need exist
from datetime import date, timedelta
def need_days():
    days = set()
    # baseline with 5-day windows beyond
    start = date(1991,12,27); end = date(2003,1,5)
    d = start
    while d <= end:
        days.add(d); d += timedelta(days=1)
    t = date(2015,6,1)
    while t <= date(2015,8,31):
        days.add(t); t += timedelta(days=1)
    return days
need = need_days()
have = {name[4:8]+name[8:10]+name[10:12] for name in names if name.startswith("sst_")}
missing = sorted([d.strftime("%Y%m%d") for d in need if d.strftime("%Y%m%d") not in have])
print("needed days:", len(need), "missing:", missing)
# sanity: any files outside expected naming?
odd = [n for n in names if not (n.startswith("sst_") and len(n)==17)]
print("odd names:", odd[:10])