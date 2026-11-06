
import fsspec, time, datetime as dt
fs = fsspec.filesystem('onedata')
B='icsa2027_data_20261101T090944Z/s1z/sst_%s.nc'
t=time.time()
ds_=[dt.date(1991,12,27),dt.date(1992,1,1),dt.date(2002,12,31),dt.date(2003,1,5),dt.date(2010,6,1),dt.date(2010,8,31),dt.date(2010,9,1)]
ok=[fs.exists(B%d.strftime('%Y%m%d')) for d in ds_]
print(ok, time.time()-t)
