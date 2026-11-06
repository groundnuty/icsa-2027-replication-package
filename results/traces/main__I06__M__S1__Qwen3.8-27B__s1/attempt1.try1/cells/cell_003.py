import os, re
base = "/data/icsa2027_data_20261101T090944Z/s1z"
files = sorted(os.listdir(base))
print(len(files))
print(files[:5], files[-5:])
import re
dates = [re.match(r'sst_(\d{8})\.nc', f).group(1) for f in files]
print(min(dates), max(dates))
# check specific dates we need
import datetime as dt
def d(s): return dt.date(int(s[:4]), int(s[4:6]), int(s[6:]))
need = [dt.date(1991,12,27)+dt.timedelta(days=i) for i in range(5)]
need += [dt.date(2003,1,1)+dt.timedelta(days=i) for i in range(5)]
for y in (1992, 2002, 2012):
    pass
missing = [dd.isoformat() for dd in need if dd.strftime('%Y%m%d') not in set(dates)]
print("missing overhang:", missing)
# check continuity for target period
tgt = [dt.date(2012,6,1)+dt.timedelta(days=i) for i in range((dt.date(2012,8,31)-dt.date(2012,6,1)).days+1)]
mt = [dd.isoformat() for dd in tgt if dd.strftime('%Y%m%d') not in set(dates)]
print("missing target:", mt)
# baseline range continuity
bl = [dt.date(1992,1,1)+dt.timedelta(days=i) for i in range((dt.date(2002,12,31)-dt.date(1992,1,1)).days+1)]
mb = [dd.isoformat() for dd in bl if dd.strftime('%Y%m%d') not in set(dates)]
print("missing baseline count:", len(mb), mb[:10], mb[-10:] if mb else "")
