import datetime as dt, json, os, time, io, h5py, numpy as np, fsspec
fs = fsspec.filesystem('onedata')
BASE='icsa2027_data_20261101T090944Z/s1z'

def build_dates(y0,m0,d0,y1,m1,d1):
    a = dt.date(y0,m0,d0); b = dt.date(y1,m1,d1)
    return [(a+dt.timedelta(days=i)).strftime('%Y%m%d') for i in range((b-a).days+1)]

ext_dates = build_dates(1991,12,27, 2003,1,5)   # 4066
tgt_dates = build_dates(2007,6,1, 2007,8,31)    # 92
all_dates = ext_dates + tgt_dates
print(len(ext_dates), len(tgt_dates), len(all_dates))

idx = json.load(open('cache/region_idx.json'))
Y0,Y1,X0,X1 = idx['y0'],idx['y1'],idx['x0'],idx['x1']
sl = (slice(Y0,Y1+1), slice(X0,X1+1))
NY, NX = Y1-Y0+1, X1-X0+1

CH=16
out_dir='cache/arr'
os.makedirs(out_dir, exist_ok=True)
manifest_path='cache/manifest.json'
manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}
todo = [d for d in all_dates if manifest.get(d) != 1]
print('todo:', len(todo))
t0=time.time(); nbatch=0
for i in range(0, len(todo), CH):
    batch = todo[i:i+CH]
    try:
        data = fs.cat([f'{BASE}/sst_{d}.nc' for d in batch])
    except Exception as e:
        print('BATCH ERR', batch[0], type(e).__name__, str(e)[:200]); raise
    for d in batch:
        b = data[f'{BASE}/sst_{d}.nc']
        f = h5py.File(io.BytesIO(b),'r')
        arr = f['analysed_sst'][0][sl[0], sl[1]]
        f.close()
        np.save(f'{out_dir}/{d}.npy', arr)
        manifest[d]=1
    nbatch+=1
    if nbatch%25==0:
        json.dump(manifest, open(manifest_path,'w'))
        print(f'{len(manifest)}/{len(all_dates)} at {time.time()-t0:.0f}s', flush=True)
json.dump(manifest, open(manifest_path,'w'))
print('DONE. total files cached:', len(manifest), 'elapsed', round(time.time()-t0,1), 's')
