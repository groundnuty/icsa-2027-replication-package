import os, shutil, datetime as dt, time, fsspec, h5py, numpy as np, hashlib, threading
from concurrent.futures import ThreadPoolExecutor

fs = fsspec.filesystem('onedata')
base='/icsa2027_data_20261101T090944Z/s1z'
LAT0,LAT1,LON0,LON1 = 322,382,485,545
EPOCH = dt.date(1981,1,1)

z=np.load('/work/extracted.npz', allow_pickle=False)
ext=z['ext']; tgt=z['tgt']; ext_t=z['ext_t']; tgt_t=z['tgt_t']
EXT=[dt.date.fromisoformat(s) for s in z['ext_dates']]
TGT=[dt.date.fromisoformat(s) for s in z['tgt_dates']]
print('loaded. missing ext:', int((ext_t==0).sum()), 'missing tgt:', int((tgt_t==0).sum()))

# reference grid md5
with fs.open(f'{base}/sst_19920101.nc','rb') as f, h5py.File(f) as h:
    ref_md5={'lat':hashlib.md5(h['latitude'][LAT0:LAT1].tobytes()).hexdigest(),
             'lon':hashlib.md5(h['longitude'][LON0:LON1].tobytes()).hexdigest()}

tl = threading.local()
def fetch(d):
    wid = getattr(tl,'wid',None)
    if wid is None:
        wid = threading.get_ident() % 100000
        tl.wid = wid
    loc=f'/work/cache/tmp_{wid}.nc'
    try:
        with fs.open(f'{base}/sst_{d:%Y%m%d}.nc','rb') as rf, open(loc,'wb') as wf:
            shutil.copyfileobj(rf, wf, 1<<20)
        with h5py.File(loc,'r') as f:
            raw=f['analysed_sst'][0, LAT0:LAT1, LON0:LON1].astype(np.float32)
            tval=int(f['time'][0])
            la=f['latitude'][LAT0:LAT1]; lo=f['longitude'][LON0:LON1]
        os.remove(loc)
        exp_t=(d-EPOCH).days*86400
        if tval!=exp_t: return ('TIME_MISMATCH',str(d),tval,exp_t)
        if hashlib.md5(la.tobytes()).hexdigest()!=ref_md5['lat'] or hashlib.md5(lo.tobytes()).hexdigest()!=ref_md5['lon']:
            return ('GRID_MISMATCH',str(d),None,None)
        return ('OK',d,raw,tval)
    except Exception as e:
        try: os.remove(loc)
        except Exception: pass
        return ('ERR',str(d),repr(e)[:100],None)

def refill(arr, tarr, dates, missing_mask):
    todo=[i for i in np.where(missing_mask)[0]]
    problems=[]
    for attempt in range(6):
        if not todo: break
        results=[]
        with ThreadPoolExecutor(max_workers=10) as ex:
            results=list(ex.map(lambda i: fetch(dates[i]), todo))
        nxt=[]
        for i,r in zip(todo,results):
            status,d,a,b=r
            if status=='OK':
                arr[i]=a; tarr[i]=b
            else:
                problems.append((status,d,a,b)); nxt.append(i)
        todo=nxt
        if todo: time.sleep(3)
    return problems, todo

p1,todo1=refill(ext,ext_t,EXT,ext_t==0)
p2,todo2=refill(tgt,tgt_t,TGT,tgt_t==0)
print('after refill: missing ext:', len(todo1), 'missing tgt:', len(todo2))
print('problem kinds ext:', sorted(set(p[0] for p in p1)), 'count', len(p1))
print('problem kinds tgt:', sorted(set(p[0] for p in p2)), 'count', len(p2))
print('sample problems:', p1[:3], p2[:3])

np.savez_compressed('/work/extracted.npz', ext=ext, tgt=tgt, ext_t=ext_t, tgt_t=tgt_t,
                    ext_dates=np.array([d.isoformat() for d in EXT]), tgt_dates=np.array([d.isoformat() for d in TGT]))
print('ext finite frac:', float(np.isfinite(ext).mean()), 'tgt finite frac:', float(np.isfinite(tgt).mean()))
print('ext time monotonic:', bool(np.all(np.diff(ext_t)>0)), 'tgt monotonic:', bool(np.all(np.diff(tgt_t)>0)))
print('ext_t zero count:', int((ext_t==0).sum()), 'tgt_t zero count:', int((tgt_t==0).sum()))
# cleanup tmps
import glob as g
for p in g.glob('/work/cache/tmp_*.nc'):
    os.remove(p)
print('cache dir now:', os.listdir('/work/cache'))
