import fsspec, h5py, numpy as np, datetime as dt, time
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
BASE='icsa2027_data_20261101T090944Z/s1z'

# locate region slice from one file
with fs.open(f'{BASE}/sst_20100601.nc','rb') as f:
    with h5py.File(f,'r') as h:
        lat = h['latitude'][:].astype('float64')
        lon = h['longitude'][:].astype('float64')
latr = np.round(lat,2); lonr = np.round(lon,2)
latmask = (latr>=60.49)&(latr<=61.69)
lonmask = (lonr>=17.25)&(lonr<=18.45)
i0,i1 = np.where(latmask)[0][[0,-1]]
j0,j1 = np.where(lonmask)[0][[0,-1]]
print('lat idx', i0,i1, 'lon idx', j0,j1, 'n', i1-i0+1, j1-j0+1)
print('lat vals', latr[i0:i1+1][:3], latr[i0:i1+1][-3:])
print('lon vals', lonr[j0:j1+1][:3], lonr[j0:j1+1][-3:])

def read_one(dstr):
    with fs.open(f'{BASE}/sst_{dstr}.nc','rb') as f:
        with h5py.File(f,'r') as h:
            a = h['analysed_sst'][0, i0:i1+1, j0:j1+1]
            t = h['time'][0]
    return dstr, int(t), np.asarray(a, dtype=np.float32)

# test 60 files with 12 threads
dstrs = [(dt.date(2010,6,1)+dt.timedelta(days=k)).strftime('%Y%m%d') for k in range(60)]
t0=time.time()
with ThreadPoolExecutor(12) as ex:
    res = list(ex.map(read_one, dstrs))
el=time.time()-t0
print(f'60 files in {el:.1f}s -> {60/el:.1f} files/s; est total for 4163: {4163*el/60:.0f}s')
# consistency checks
ok=True
for dstr, t, a in res:
    d = dt.datetime.strptime(dstr,'%Y%m%d')
    expect = (d - dt.date(1981,1,1)).days*86400
    if t != expect: print('TIME MISMATCH', dstr, t, expect); ok=False
    if a.shape != (60,60): print('SHAPE', dstr, a.shape); ok=False
print('time/shape consistent:', ok)
print('nan frac sample', np.isnan(res[0][2]).mean())
