import fsspec, h5py, numpy as np, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# file list
names = sorted(e.split('/')[-1] for e in fs.ls(base))
print("n files", len(names), names[0], names[-1])
dates = np.array([n[4:8]+'-'+n[8:10]+'-'+n[10:12] for n in names])
import datetime as dt
d0 = dt.date(1982,1,1); d1 = dt.date(2023,12,31)
alldates = [(d0 + dt.timedelta(days=i)).isoformat() for i in range((d1-d0).days+1)]
missing = set(alldates) - set(dates.tolist())
extra = set(dates.tolist()) - set(alldates)
print("missing:", len(missing), "extra:", len(extra))
need = alldates[alldates.index('1991-12-27'):alldates.index('2003-01-05')+1] + alldates[alldates.index('2021-06-01'):alldates.index('2021-08-31')+1]
print("needed files:", len(need), "all present:", all(f'sst_{d.replace("-","")}.nc' in set(names) for d in need))

# grid consistency check across sample files
ref = None
for d in ['19820101','19920229','19961231','20030105','20210601','20230831']:
    p = f'{base}/sst_{d}.nc'
    with fs.open(p,'rb') as f:
        hf = h5py.File(f,'r')
        la = hf['latitude'][:]; lo = hf['longitude'][:]
        tv = hf['time'][:]
        hf.close()
    if ref is None:
        ref = (la.copy(), lo.copy())
        print("time value sample:", tv)
    else:
        assert np.array_equal(la, ref[0]) and np.array_equal(lo, ref[1]), d
print("grid consistent on samples")
