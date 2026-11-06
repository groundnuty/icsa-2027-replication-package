import numpy as np
from datetime import date, timedelta
st = np.load('/tmp/stage2.npz')
data = np.load('/tmp/chunk1.npy')
def daterange(a,b):
    out=[]; d=a
    while d<=b: out.append(d); d+=timedelta(days=1)
    return out
bd_ext = daterange(date(1991,12,27), date(2003,1,5))
target_dates = daterange(date(2013,6,1), date(2013,8,31))
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
key = lambda dt: cum[dt.month-1]+dt.day
idx_of = {dt:i for i,dt in enumerate(bd_ext)}
NBASE=len(bd_ext); V=data[:NBASE]; TGT=data[NBASE:]; NC=3600
tk = np.array([key(d) for d in target_dates])
idx = np.arange(92)[:,None]
def prev_true(m): return np.maximum.accumulate(np.where(m, idx, -1), axis=0)
def next_true(m): return np.minimum.accumulate(np.where(m, idx, 92)[::-1], axis=0)[::-1]
def detect(hotb):
    pn = prev_true(~hotb); nn = next_true(~hotb)
    cores = hotb & ((nn-pn-1) >= 5)
    pc, nc = prev_true(cores), next_true(cores)
    return cores | ((~cores) & (pc>=0) & (nc<=91) & ((nc-pc-1)<=2))
def events_of(M):
    act = M.sum(axis=1).astype(bool)
    ev=[]; i=0
    while i<92:
        if act[i]:
            j=i
            while j+1<92 and act[j+1]: j+=1
            ev.append((i,j)); i=j+1
        else: i+=1
    return ev

def pools(d, include_ext=True):
    out=[]
    for s in [dt for dt in bd_ext if key(dt)==d and 1992<=dt.year<=2002]:
        o=idx_of[s]
        for k in range(o-5,o+6):
            if include_ext or bd_ext[k].year<=2002:
                out.append(k)
    return np.array(out)

def thresholds(include_ext=True):
    thr=np.full((366,NC), np.nan); cols=np.arange(NC)
    for d in range(1,367):
        if d==60: continue
        pi = pools(d, include_ext)
        P=V[pi].reshape(len(pi),NC)
        n=np.isfinite(P).sum(0); S=np.sort(P,axis=0)
        h=n*0.9+0.5; lo=np.floor(h).astype(np.int64); g=h-lo
        q=(1-g)*S[np.clip(lo-1,0,np.maximum(n-1,0)),cols]+g*S[np.clip(lo,0,np.maximum(n-1,0)),cols]
        thr[d-1]=np.where(n>0,q,np.nan)
    thr[59]=0.5*(thr[58]+thr[60])
    a3=np.tile(thr,(3,1)); c=np.zeros((a3.shape[0]+1,NC)); np.cumsum(a3,axis=0,out=c[1:])
    d0=np.arange(366)
    return (c[d0+382]-c[d0+351])/31.0

thrA = thresholds(True)   # as used
thrB = thresholds(False)  # exclude 2003 extension values
T = TGT.reshape(92,NC)
for label, thr, strict in [("A: >=, ext included (used)", thrA, False),
                           ("B: >=, ext excluded",       thrB, False),
                           ("S: >,  ext included (strict)", thrA, True)]:
    hot = (T>thr[tk-1] if strict else T>=thr[tk-1])
    hot &= np.isfinite(T)&np.isfinite(thr[tk-1])
    M = detect(hot)
    ev = events_of(M)
    print(f"{label}: hot={int(hot.sum())}, MHW cell-days={int(M.sum())}, events={[(str(target_dates[a]),str(target_dates[b])) for a,b in ev]}")

diff = np.abs(thrA[tk-1]-thrB[tk-1])
print("thrA vs thrB max abs diff: %.4f K, mean %.4f K" % (np.nanmax(diff), np.nanmean(diff)))
