import os,re,datetime as dt
d='/data/icsa2027_data_20261101T090944Z/s1z'
fs=sorted(os.listdir(d)); print(fs[0],fs[-1],len(fs)); print([f for f in fs if not f.startswith('sst_')][:10])
dates=[f[4:12] for f in fs if re.match(r'sst_\d{8}\.nc$',f)]
print(len(dates), dates[0], dates[-1])
s=set(dates)
exp=[(dt.date(1991,12,27)+dt.timedelta(i)).strftime('%Y%m%d') for i in range((dt.date(2016,8,31)-dt.date(1991,12,27)).days+1)]
miss=[e for e in exp if e not in s]; print(len(miss), miss[:20])