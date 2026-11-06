
import fsspec, datetime, os
fs = fsspec.filesystem('onedata')
path = "icsa2027_data_20261101T090944Z/s1z"
ls = fs.ls(path)
bases = [os.path.basename(f) for f in ls]
years = sorted({b[4:8] for b in bases if b.startswith("sst_")})
print("years:", years)
names = set(bases)
need = [datetime.date(1991,12,27)+datetime.timedelta(days=i) for i in range(5)]
need += [datetime.date(2003,1,1)+datetime.timedelta(days=i) for i in range(5)]
need += [datetime.date(1992,1,1), datetime.date(2002,12,31), datetime.date(2007,6,1), datetime.date(2007,8,31)]
for d in need:
    print(d, d.strftime("sst_%Y%m%d.nc") in names)
# check full span
ds = [datetime.datetime.strptime(b[4:12], "%Y%m%d").date() for b in bases if b.startswith("sst_")]
print("min date:", min(ds), "max date:", max(ds), "count:", len(ds))
