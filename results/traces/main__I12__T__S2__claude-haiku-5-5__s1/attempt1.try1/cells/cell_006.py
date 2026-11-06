
import warnings; warnings.filterwarnings('ignore')
os.makedirs('output', exist_ok=True)
V = sub.values.astype(np.float64)           # (T,60,60)
T = len(t)
doy = np.array([x.replace(year=2000).dayofyear for x in t])  # leap-year mapping, Feb29=60
base_idx = np.where((t>=pd.Timestamp('1992-01-01'))&(t<=pd.Timestamp('2002-12-31')))[0]
pools = {d: set() for d in range(1,367) if d!=60}
tt = t.values.astype('datetime64[D]')
for b in base_idx:
    d = doy[b]
    if d==60: continue
    lo_, hi_ = b-5, b+5   # daily index, contiguous series
    pools[d].update(range(max(lo_,0), min(hi_,T-1)+1))
thr = np.full((367,60,60), np.nan); clim = np.full((367,60,60), np.nan)
for d in range(1,367):
    if d==60: continue
    idx = np.array(sorted(pools[d]))
    P = V[idx]
    thr[d] = np.nanpercentile(P, 90, axis=0, method='hazen')
    clim[d] = np.nanmean(P, axis=0)
thr[60] = (thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):  # a: (367,...) index 1..366
    arr = a[1:]
    ext = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    cs = np.stack([ext[i:i+31].mean(axis=0) for i in range(366)])
    out = np.full_like(a, np.nan); out[1:] = cs; return out
thr_s = smooth(thr); clim_s = smooth(clim)

# target
tgt = np.where((t>=pd.Timestamp('2009-06-01'))&(t<=pd.Timestamp('2009-08-31')))[0]
Vt = V[tgt]; tdoy = doy[tgt]; tdates = t[tgt]
sea = np.all(np.isfinite(Vt), axis=0)
print('sea cells', sea.sum(), 'target days', len(tgt))
hot = (Vt >= thr_s[tdoy]) & sea[None]    # (days,60,60)
hot &= np.isfinite(thr_s[tdoy])
mhw = np.zeros_like(hot)
for i in range(60):
    for j in range(60):
        if not sea[i,j]: continue
        h = hot[:,i,j]
        runs=[]; k=0; n=len(h)
        while k<n:
            if h[k]:
                s=k
                while k<n and h[k]: k+=1
                if k-s>=5: runs.append([s,k-1])
            else: k+=1
        merged=[]
        for r in runs:
            if merged and r[0]-merged[-1][1]-1<=2: merged[-1][1]=r[1]
            else: merged.append(list(r))
        for s,e in merged: mhw[s:e+1,i,j]=True
active = mhw.any(axis=(1,2))
events=[]; k=0; n=len(active)
while k<n:
    if active[k]:
        s=k
        while k<n and active[k]: k+=1
        events.append({"onset":str(tdates[s].date()),"end":str(tdates[k-1].date())})
    else: k+=1
print(events, mhw.sum())
