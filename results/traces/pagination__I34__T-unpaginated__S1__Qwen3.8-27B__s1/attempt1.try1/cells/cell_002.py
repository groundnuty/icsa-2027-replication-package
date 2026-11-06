
import fsspec
fs = fsspec.filesystem('onedata')
path = "icsa2027_data_20261101T090944Z/s1z"
ls = fs.ls(path)
print("total files:", len(ls))
years = sorted({f.split("sst_")[1][:4] for f in ls if f.startswith("sst_")})
print("years:", years)
# check specific needed dates
import datetime
need = [datetime.date(1991,12,27)+datetime.timedelta(days=i) for i in range(5)]
need += [datetime.date(2003,1,1)+datetime.timedelta(days=i) for i in range(5)]
need += [datetime.date(1992,1,1), datetime.date(2002,12,31)]
need += [datetime.date(2007,6,1), datetime.date(2007,8,31)]
for d in need:
    print(d, d.strftime("sst_%Y%m%d.nc") in set(ls))
