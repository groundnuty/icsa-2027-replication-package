import fsspec, datetime
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'
def dr(a,b):
    d=a
    while d<=b:
        yield d; d+=datetime.timedelta(1)
need=list(dr(datetime.date(1991,12,27),datetime.date(2003,1,5)))+list(dr(datetime.date(2014,5,27),datetime.date(2014,9,5)))
miss=[d for d in need if not fs.exists(f"{base}/sst_{d:%Y%m%d}.nc")]
print(len(need),'missing',len(miss),[str(m) for m in miss[:30]])