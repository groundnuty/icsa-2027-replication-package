
import fsspec, time
fs = fsspec.filesystem('onedata')
B='icsa2027_data_20261101T090944Z/s1z/sst_%s.nc'
d0=dt.date(1991,12,27); d1=dt.date(2003,1,5)
need=[(d0+dt.timedelta(i)) for i in range((d1-d0).days+1)]
t=time.time()
t2=[dt.date(2010,6,1)+dt.timedelta(i) for i in range(92)]
t2=[d for d in need] # placeholder
ok=[fs.exists(B%d.strftime('%Y%m%d')) for d in [dt.date(1991,12,27),dt.date(1992,1,1),dt.date(2002,12,31),dt.date(2003,1,5),dt.date(2010,6,1),dt.date(2010,8,31),dt.date(2010,9,1)]]
print(ok, time.time()-t)
