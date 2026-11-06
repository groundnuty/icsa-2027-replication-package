script = r'''
import numpy as np, datetime as dt, json, time

CACHE='/work/cache'
thr_raw=np.load(f'{CACHE}/thr_raw.npy'); clim_raw=np.load(f'{CACHE}/clim_raw.npy')
raw_t=np.load(f'{CACHE}/raw_target.npy')
sea = np.isfinite(raw_t).all(axis=0)

for arr in (thr_raw, clim_raw):
    arr[59] = 0.5*(arr[58]+arr[60])
print('after fill: thr doy60 sample', thr_raw[59,30,30], ' clim doy60 sample', clim_raw[59,30,30])
print('doy60 all-sea finite:', np.all(np.isfinite(thr_raw[59][sea])), np.all(np.isfinite(clim_raw[59][sea])))

offs = np.arange(-15,16)
def circ_smooth(A):
    stack = np.stack([np.roll(A, -o, axis=0) for o in offs], axis=0)
    with np.errstate(invalid='ignore'):
        out = np.nanmean(stack, axis=0)
    return out
t0=time.time()
thr = circ_smooth(thr_raw); clim = circ_smooth(clim_raw)
print('smoothing done', f'{time.time()-t0:.1f}s')
print('thr/clim finite everywhere on sea:', np.all(np.isfinite(thr[:,sea])), np.all(np.isfinite(clim[:,sea])))
print('clim sample Jun-Aug:', [f'{clim[d,30,30]:.2f}' for d in [152,182,213,243]])
print('thr sample Jun-Aug:', [f'{thr[d,30,30]:.2f}' for d in [152,182,213,243]])
np.save(f'{CACHE}/thr_smooth.npy',thr); np.save(f'{CACHE}/clim_smooth.npy',clim)

sst = raw_t
T = np.stack([thr[doy-1] for doy in range(153,245)], axis=0)
hot = sst >= T
print('hot days total (all cells):', int(hot.sum()))

def runs_mask_1d(h):
    n=h.size; out=np.zeros(n,bool); i=0
    while i<n:
        if h[i]:
            j=i
            while j<n and h[j]: j+=1
            if j-i>=5: out[i:j]=True
            i=j
        else: i+=1
    return out

def join_gaps_1d(m):
    m=m.copy(); n=m.size; i=0
    while i<n:
        if m[i]:
            j=i
            while j<n and m[j]: j+=1
            if j<n:
                k=j
                while k<n and not m[k]: k+=1
                if k<n and (k-j)<=2:
                    m[j:k]=True
                    i=k; continue
            i=j
        else: i+=1
    return m

per_cell = np.zeros_like(hot)
for a in range(60):
    for b in range(60):
        if not sea[a,b]: continue
        m = runs_mask_1d(hot[:,a,b])
        if m.any():
            per_cell[:,a,b] = join_gaps_1d(m)
print('per-cell MHW cell-days:', int(per_cell.sum()))
print('cells with any per-cell MHW:', int(per_cell.any(axis=0).sum()))
np.save(f'{CACHE}/per_cell.npy', per_cell)

active = per_cell.any(axis=(1,2))
print('active days:', int(active.sum()), 'of', int(active.size))
events=[]
i=0; n=active.size
dates=[dt.date(2008,6,1)+dt.timedelta(days=k) for k in range(n)]
while i<n:
    if active[i]:
        j=i
        while j<n and active[j]: j+=1
        events.append((dates[i], dates[j-1]))
        i=j
    else: i+=1
for e in events: print('event:', e[0], '->', e[1], 'length', (e[1]-e[0]).days+1)
json.dump([[str(a),str(b)] for a,b in events], open(f'{CACHE}/events.json','w'))
print('DONE_STAGE3')
'''
open('/work/stage3.py','w').write(script)
import subprocess
r=subprocess.run(['python','/work/stage3.py'],capture_output=True,text=True)
print(r.stdout[-4000:]); print(r.stderr[-2000:])
