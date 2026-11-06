import fsspec, time
from datetime import date, timedelta
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

def daterange(a, b):
    out=[]; d=a
    while d<=b:
        out.append(d); d+=timedelta(days=1)
    return out

need = daterange(date(1991,12,27), date(2003,1,5)) + daterange(date(2013,6,1), date(2013,8,31))
print("needed files:", len(need))
t0=time.time()
missing=[]
for i,d in enumerate(need):
    nm = f'sst_{d:%Y%m%d}.nc'
    try:
        fs.info(f'{base}/{nm}')
    except Exception:
        missing.append(nm)
    if i==99:
        print(f"100 infos in {time.time()-t0:.2f}s")
print("total missing:", len(missing), missing[:10])
