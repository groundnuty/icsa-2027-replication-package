import datetime
def dr(a,b):
    d=a
    while d<=b:
        yield d; d+=datetime.timedelta(1)
need=list(dr(datetime.date(1991,12,27),datetime.date(2003,1,5)))+list(dr(datetime.date(2014,5,27),datetime.date(2014,9,5)))
miss=[]
for d in need:
    if not fs.exists(f"{base}/sst_{d:%Y%m%d}.nc"): miss.append(d)
print(len(need), 'missing', miss[:30], len(miss))