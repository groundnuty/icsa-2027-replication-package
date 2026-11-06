import os, shutil, datetime as dt, time, fsspec, h5py, numpy as np
from concurrent.futures import ThreadPoolExecutor

fs = fsspec.filesystem('onedata')
base='/icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/cache', exist_ok=True)
LAT0,LAT1,LON0,LON1 = 322,382,485,545
NW=12
EPOCH = dt.date(1981,1,1)

def daterange(a,b):
    out=[]; d=a
    while d<=b:
        out.append(d); d+=dt.timedelta(days=1)
    return out

EXT = daterange(dt.date(1991,12,27), dt.date(2003,1,5))
TGT = daterange(dt.date(2009,6,1), dt.date(2009,8,31))
ALL = EXT + TGT

ref_md5 = {}
def fetch(d, wid):
    loc=f'/work/cache/tmp{wid}.nc'
    try:
        with fs.open(f'{base}/sst_{d:%Y%m%d}.nc','rb') as rf, open(loc,'wb') as wf:
            shutil.copyfileobj(rf, wf, 1<<20)
        with h5py.File(loc,'r') as f:
            raw=f['analysed_sst'][0, LAT0:LAT1, LON0:LON1].astype(np.float32)
            tval=int(f['time'][0])
            la=f['latitude'][:]; lo=f['longitude'][:]
        os.remove(loc)
        # integrity checks
        exp_t = (d - EPOCH).days * 86400
        if tval != exp_t:
            return ('TIME_MISMATCH', d, tval, exp_t)
        if ref_md5:
            import hashlib
            if hashlib.md5(la.tobytes()).hexdigest()!=ref_md5['lat'] or hashlib.md5(lo.tobytes()).hexdigest()!=ref_md5['lon']:
                return ('GRID_MISMATCH', d, None, None)
        else:
            import hashlib
            ref_md5['lat']=hashlib.md5(la.tobytes()).hexdigest()
            ref_md5['lon']=hashlib.md5(lo.tobytes()).hexdigest()
        return ('OK', d, raw, tval)
    except Exception as e:
        try: os.remove(loc)
        except Exception: pass
        return ('ERR', d, repr(e)[:120], None)

ext_arr=np.full((len(EXT),60,60), np.nan, dtype=np.float32)
tgt_arr=np.full((len(TGT),60,60), np.nan, dtype=np.float32)
ext_t=np.zeros(len(EXT), dtype=np.int64); tgt_t=np.zeros(len(TGT), dtype=np.int64)
ext_idx={d:i for i,d in enumerate(EXT)}; tgt_idx={d:i for i,d in enumerate(TGT)}

t0=time.time()
todo=list(range(len(ALL)))
problems=[]
attempt=0
while todo and attempt<4:
    attempt+=1
    with ThreadPoolExecutor(max_workers=NW) as ex:
        results=list(ex.map(lambda i: fetch(ALL[i], i%NW), todo))
    nxt=[]
    for i,r in zip(todo,results):
        status,d,a,b = r
        if status=='OK':
            if d in ext_idx:
                ext_arr[ext_idx[d]]=a; ext_t[ext_idx[d]]=b
            else:
                tgt_arr[tgt_idx[d]]=a; tgt_t[tgt_idx[d]]=b
        else:
            problems.append((status,str(d),a,b))
            nxt.append(i)
    todo=nxt
    if todo:
        print(f'attempt {attempt}: {len(todo)} still failing; sample:', problems[-3:])
        time.sleep(2)
el=time.time()-t0
print(f'downloaded {len(ALL)-len(todo)}/{len(ALL)} files in {el:.1f}s ({el/len(ALL)*1000:.0f} ms/file)')
print('remaining failures:', [(s,str(d)) for s,d,a,b in problems][:10])

# cleanup tmp files
for wid in range(NW):
    p=f'/work/cache/tmp{wid}.nc'
    if os.path.exists(p): os.remove(p)

np.savez_compressed('/work/extracted.npz', ext=ext_arr, tgt=tgt_arr, ext_t=ext_t, tgt_t=tgt_t,
                    ext_dates=np.array([d.isoformat() for d in EXT]), tgt_dates=np.array([d.isoformat() for d in TGT]))
print('saved npz size MB:', round(os.path.getsize('/work/extracted.npz')/1e6,1))
print('ext finite frac:', float(np.isfinite(ext_arr).mean()), 'tgt finite frac:', float(np.isfinite(tgt_arr).mean()))
print('ext time monotonic:', bool(np.all(np.diff(ext_t)>0)), 'tgt time monotonic:', bool(np.all(np.diff(tgt_t)>0)))
print('ext time first/last:', ext_t[0], ext_t[-1], 'expect', (EXT[0]-EPOCH).days*86400, (EXT[-1]-EPOCH).days*86400)
print('tgt time first/last:', tgt_t[0], tgt_t[-1], 'expect', (TGT[0]-EPOCH).days*86400, (TGT[-1]-EPOCH).days*86400)
print('problems total:', len(problems))
