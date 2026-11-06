import numpy as np, json, datetime as dt
dates = json.load(open('cache/dates.json')); tgt_s = dates['tgt_s']
SST_t = np.load('cache/SST_t.npy'); thr_s = np.load('cache/thr_s.npy'); clim_s = np.load('cache/clim_s.npy')
mhw = np.load('cache/mhw.npy'); sea = np.load('cache/sea.npy')
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
doy_tgt = np.array([cum[int(s[4:6])-1]+int(s[6:]) for s in tgt_s])
thr_t = thr_s[doy_tgt-1]

def dstr(s): return f'{s[:4]}-{s[4:6]}-{s[6:]}'
# inspect a central cell during the event
i,j = 30,30
print('cell (30,30) sea?', bool(sea[i,j]))
for t in range(2, 18):
    s = tgt_s[t]
    print(dstr(s), f'doy={doy_tgt[t]}', f'SST={SST_t[t,i,j]:.3f}', f'thr={thr_t[t,i,j]:.3f}',
          f'clim={clim_s[doy_tgt[t]-1,i,j]:.3f}', f'hot={SST_t[t,i,j]>=thr_t[t,i,j]}', f'mhw={mhw[t,i,j]}')

# synthetic test of run>=5 & join<=2 logic (re-derive for one cell and compare)
def detect(h):
    T=len(h); m=np.zeros(T,np.uint8)
    idx=np.where(h)[0]
    if idx.size==0: return m
    br=np.where(np.diff(idx)>1)[0]
    st=np.r_[idx[0],idx[br+1]]; en=np.r_[idx[br],idx[-1]]
    keep=(en-st+1)>=5
    if not keep.any(): return m
    st,en=st[keep],en[keep]
    cs,ce=st[0],en[0]
    segs=[]
    for k in range(1,len(st)):
        if st[k]-ce-1<=2: ce=en[k]
        else: segs.append((cs,ce)); cs,ce=st[k],en[k]
    segs.append((cs,ce))
    for a,b in segs: m[a:b+1]=1
    return m
tests = [
    ([1,1,1,1,1,0,0,0,1,1,1,1,1], 2),      # gap 3 -> two events
    ([1,1,1,1,1,0,1,1,1,1,1], 1),          # gap 1 -> joined
    ([1,1,1,1,0,1,1,1,1,1,0,0,1,1,1,1,1], 1),  # gaps 1,2 -> joined
    ([1,1,1,1,0,0,1,1,1,1,0,0,0,1,1,1,1,1], 2), # gap 2 join; gap 3 split
    ([1,1,1,1,0,1,1,1,1,1], 1),            # run 4 + gap1 + run5 -> join into 10
    ([1,1,1,1,1,1,1,1,1,1,1], 1),
    ([1,1,1,1], 0),
    ([0,0,1,1,1,1,1,0,0,0,0,1,1,1,1,1,0,0,1,1,1,1,1], 3),
]
ok=True
for k,(h,nexp) in enumerate(tests):
    m=detect(np.array(h,bool)); n=0; prev=0
    for v in m:
        if v and not prev: n+=1
        prev=v
    ok &= (n==nexp)
    print(f'test{k}: events={n} expected={nexp}', 'OK' if n==nexp else 'FAIL')
print('all logic tests passed:', ok)

# distribution of per-cell MHW lengths among sea cells
lens=[]
for i in range(60):
    for j in range(60):
        if not sea[i,j]: continue
        col=mhw[:,i,j]; idx=np.where(col)[0]
        if idx.size==0: continue
        br=np.where(np.diff(idx)>1)[0]
        st=np.r_[idx[0],idx[br+1]]; en=np.r_[idx[br],idx[-1]]
        lens += (en-st+1).tolist()
import collections
print('per-cell MHW segment length counter:', dict(sorted(collections.Counter(lens).items())))
print('total per-cell segments:', len(lens))
