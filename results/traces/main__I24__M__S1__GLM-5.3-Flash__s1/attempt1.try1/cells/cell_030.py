import numpy as np, datetime as dt, time as time_mod

def hazen_rows(P):
    fin = np.isfinite(P)
    nv = fin.sum(axis=1)
    S = np.sort(np.where(fin, P, np.inf), axis=1)
    n = nv.astype(np.float64)
    virtual = n*0.9 + (0.5 + 0.9*(1 - 0.5 - 0.5)) - 1.0
    previous = np.floor(virtual).astype(np.int64)
    nxt = previous + 1
    above = virtual >= (nv - 1)
    previous = np.where(above, -1, previous)
    nxt = np.where(above, -1, nxt)
    below = virtual < 0
    previous = np.where(below, 0, previous)
    nxt = np.where(below, 0, nxt)
    last = np.maximum(nv - 1, 0).astype(np.int64)
    previous_m = np.where(previous == -1, last, previous)
    nxt_m = np.where(nxt == -1, last, nxt)
    gamma = virtual - previous.astype(np.float64)
    rows = np.arange(P.shape[0])
    a = S[rows, previous_m]
    b = S[rows, nxt_m]
    diff_b_a = b - a
    l = a + diff_b_a * gamma
    l = np.where(gamma >= 0.5, b - diff_b_a * (1 - gamma), l)
    l[nv == 0] = np.nan
    return l

def nanmean_rows(P):
    fin = np.isfinite(P)
    P0 = np.where(fin, P, 0.0)
    tot = P0.sum(axis=1)
    cnt = fin.sum(axis=1)
    with np.errstate(invalid='ignore', divide='ignore'):
        avg = tot / cnt
    avg[cnt == 0] = np.nan
    return avg

A=np.load('/tmp/A_all.npy'); ords=np.load('/tmp/dates_ord.npy')
dates=[dt.date.fromordinal(int(o)) for o in ords]
T=A.shape[0]; Aflat=A.reshape(T,-1)
NC=Aflat.shape[1]
def doy_map(d):
    y=d.timetuple().tm_yday
    leap = d.year%4==0 and (d.year%100!=0 or d.year%400==0)
    return y if leap else (y+1 if y>=60 else y)
doy=np.array([doy_map(d) for d in dates])
b0=dt.date(1992,1,1); b1=dt.date(2002,12,31)
base_idx=np.array([i for i,d in enumerate(dates) if b0<=d<=b1])
base_doy=doy[base_idx]
list_d={d: base_idx[base_doy==d] for d in range(1,367)}
offs=np.arange(-5,6)
thr_raw=np.full((366,NC),np.nan)
clim_raw=np.full((366,NC),np.nan)
t0=time_mod.time()
for d in range(1,367):
    idxs=list_d[d]
    if len(idxs)==0: continue
    P=Aflat[idxs[:,None]+offs[None,:],:]
    P=np.ascontiguousarray(P.reshape(len(idxs)*11,NC).T)   # (NC, pool), C-contiguous
    thr_raw[d-1]=hazen_rows(P)
    clim_raw[d-1]=nanmean_rows(P)
print('pool loop %.1fs'%(time_mod.time()-t0))
# fill day 60 (index 59) with mean of days 59 and 61
thr_raw[59]=0.5*(thr_raw[58]+thr_raw[60])
clim_raw[59]=0.5*(clim_raw[58]+clim_raw[60])
print('NaNs after fill: thr',int(np.isnan(thr_raw).sum()),'clim',int(np.isnan(clim_raw).sum()))
# NaN structure: only land cells
land = np.isnan(A).all(axis=0).reshape(-1)
print('land cells:',int(land.sum()), 'thr NaN cols all land?', np.array_equal(np.isnan(thr_raw).any(axis=0), land), 'thr NaN rows?', np.isnan(thr_raw).any(axis=1).any())
np.save('/tmp/thr_raw.npy',thr_raw); np.save('/tmp/clim_raw.npy',clim_raw)
print('cell0 (57.58N/10.26E) thr doy 1,152,366:', thr_raw[[0,151,365],0])
print('cell0 clim doy 1,152,366:', clim_raw[[0,151,365],0])
