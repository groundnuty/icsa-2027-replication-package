import fsspec, re, os, datetime as dt
fs = fsspec.filesystem('onedata')
allf = fs.find('icsa2027_data_20261101T090944Z/s1z')
print(len(allf))
names = sorted(f.split('/')[-1] for f in allf if f.endswith('.nc'))
print(len(names), names[0], names[-1])
dates=set(re.findall(r'sst_(\d{8})\.nc',' '.join(names)))
need=[]
d=dt.date(1991,12,27)
while d<=dt.date(2012,8,31):
    need.append(d.strftime('%Y%m%d')); d+=dt.timedelta(1)
miss=[x for x in need if x not in dates]
print(len(need),len(miss), miss[:5], miss[-5:])