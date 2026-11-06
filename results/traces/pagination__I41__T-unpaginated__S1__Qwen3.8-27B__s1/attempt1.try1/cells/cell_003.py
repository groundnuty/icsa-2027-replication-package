
import fsspec, h5py, time
fs = fsspec.filesystem('onedata')

# Check h5 layout of one file
path = '/icsa2027_data_20261101T090944Z/s1z/sst_20210701.nc'
with fs.open(path, "rb") as f:
    h = h5py.File(f, "r")
    print("keys:", list(h.keys()))
    v = h['analysed_sst']
    print("shape:", v.shape, "dtype:", v.dtype)
    print("chunks:", v.chunks, "compression:", v.compression)
    print("fills:", v.fillvalue)
    h.close()

# list all files and check needed dates exist
files = [x.rsplit('/',1)[-1] for x in fs.ls('/icsa2027_data_20261101T090944Z/s1z')]
import re
dates = sorted(f[4:12] for f in files if f.startswith('sst_') and f.endswith('.nc'))
print("n files:", len(dates), "first:", dates[0], "last:", dates[-1])

def daterange(y0,m0,d0,y1,m1,d1):
    from datetime import date, timedelta
    a = date(y0,m0,d0); b = date(y1,m1,d1); out=[]
    while a<=b: out.append(a); a+=timedelta(days=1)
    return out

need = daterange(1991,12,27,2003,1,5) + daterange(2021,6,1,2021,8,31)
needset = {d.strftime('%Y%m%d') for d in need}
missing = sorted(needset - set(dates))
print("needed:", len(needset), "missing:", missing[:20], "count_missing:", len(missing))
print("leap years in range:", [y for y in (1992,1996,2000,2002,2021) ])
