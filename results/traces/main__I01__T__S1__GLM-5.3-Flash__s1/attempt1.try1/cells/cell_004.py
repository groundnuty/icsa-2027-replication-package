import fsspec, datetime as dt
fs = fsspec.filesystem('onedata')
path2 = 'icsa2027_data_20261101T090944Z/s2z'
listing2 = fs.ls(path2, detail=False)
print('n listed:', len(listing2))
print('first:', listing2[:2])
print('last:', listing2[-2:])
setl2 = set(listing2)
def fname(p,d): return f"{p}/sst_{d:%Y%m%d}.nc"
need = []
d = dt.date(1991,12,27)
while d <= dt.date(2003,1,5):
    need.append(('b', d)); d += dt.timedelta(days=1)
d = dt.date(2008,6,1)
while d <= dt.date(2008,8,31):
    need.append(('t', d)); d += dt.timedelta(days=1)
miss_b = [fname(path2,d) for k,d in need if k=='b' and fname(path2,d) not in setl2]
miss_t = [fname(path2,d) for k,d in need if k=='t' and fname(path2,d) not in setl2]
print('missing baseline in s2z:', len(miss_b), miss_b[:3])
print('missing target in s2z:', len(miss_t), miss_t[:3])
