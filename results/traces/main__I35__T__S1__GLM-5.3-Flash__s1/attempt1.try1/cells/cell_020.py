import numpy as np, datetime as dt, calendar, time, json
from numpy.lib.stride_tricks import sliding_window_view
import warnings

t_start=time.time()
z=np.load('/work/extracted.npz', allow_pickle=False)
ext=z['ext']; tgt=z['tgt']
EXT=[dt.date.fromisoformat(s) for s in z['ext_dates']]
TGT=[dt.date.fromisoformat(s) for s in z['tgt_dates']]
NT,NC = 92,60,60
NT=len(TGT)

def doy_of(d):
    y=d.timetuple().tm_yday
    if calendar.isleap(d.year): return y
    return y+1 if y>=60 else y

ext_doy0=np.array([doy_of(d)-1 for d in EXT])  # 0-based doy, 0..365
tgt_doy0=np.array([doy_of(d)-1 for d in TGT])
print('ext_doy0 range', ext_doy0.min(), ext_doy0.max(), 'unique count', len(np.unique(ext_doy0)))
print('target doy0s:', tgt_doy0.min(), '..', tgt_doy0.max(), 'n unique', len(np.unique(tgt_doy0)))

# ---- pool index matrix: idx[d0, k] = EXT index for k-th value in pool of doy0=d0
idx=np.zeros((366,121), dtype=np.int32)
counts=np.zeros(366, dtype=np.int32)
for i,w in enumerate(ext_doy0):
    for o in range(-5,6):
        d0=(w+o)%366
        idx[d0, counts[d0]] = i
        counts[d0]+=1
print('pool sizes: min', counts.min(), 'max', counts.max(), 'doy60(0-based 59) count', counts[59])
assert counts[59]==0 and set(np.unique(counts))=={0,121}

# ---- sea cells
sea=np.all(np.isfinite(tgt), axis=0)  # (60,60)
sea_idx=np.where(sea.ravel())[0]
print('sea cells:', len(sea_idx))

ext_sea = ext.reshape(ext.shape[0], -1)[:, sea_idx]  # (4028, nsea) float32
tgt_sea = tgt.reshape(tgt.shape[0], -1)[:, sea_idx]  # (92, nsea) float32
print('ext_sea', ext_sea.shape, 'any NaN on sea cells:', bool(np.isnan(ext_sea).any()))

# ---- chunked threshold & climatology
nsea=len(sea_idx)
thr_raw=np.full((366,nsea), np.nan); clim_raw=np.full((366,nsea), np.nan)
CH=300
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    for c0 in range(0, nsea, CH):
        cc=slice(c0, min(c0+CH, nsea))
        chunk = ext_sea[:, cc]                     # (4028, ch)
        pools = chunk[idx]                          # (366,121,ch) float32
        p64 = pools.astype(np.float64)
        thr_raw[cc if False else slice(None), cc] = 0  # placeholder (avoid mistake)
        thr_raw[:, cc] = np.nanpercentile(p64, 90, axis=1, method='hazen')
        clim_raw[:, cc] = np.nanmean(p64, axis=1)
        del pools, p64
# day 60 (0-based 59): pool was dummy (index 0 values) -> overwrite with NaN then fix
thr_raw[59]=np.nan; clim_raw[59]=np.nan
print('day60 NaN before fix:', np.isnan(thr_raw).any(axis=0).sum(), np.isnan(clim_raw).any(axis=0).sum())
thr_raw[59] = 0.5*(thr_raw[58]+thr_raw[60])
clim_raw[59] = 0.5*(clim_raw[58]+clim_raw[60])
print('day60 NaN after fix:', np.isnan(thr_raw).any(), np.isnan(clim_raw).any())

# ---- 31-day circular moving mean
def circ_smooth(a):  # a (366, n)
    pad=np.concatenate([a[-15:], a, a[:15]], axis=0)
    win=sliding_window_view(pad, 31, axis=0)   # (366, n, 31)
    return win.mean(axis=2)
thr_sm=circ_smooth(thr_raw)
clim_sm=circ_smooth(clim_raw)
print('thr_sm finite:', np.isfinite(thr_sm).all(), 'clim_sm finite:', np.isfinite(clim_sm).all())

# ---- hot days: target SST (float64) >= smoothed threshold for that doy
hot = np.empty((NT, nsea), dtype=bool)
for t in range(NT):
    hot[t] = tgt_sea[t].astype(np.float64) >= thr_sm[tgt_doy0[t]]
print('hot day-cell fraction:', float(hot.mean()))

# ---- per-cell MHW: runs>=5, join gaps<=2
def cell_mhw(hot_row):
    hp=np.concatenate(([False], hot_row, [False]))
    d=np.diff(hp.astype(np.int8))
    starts=np.where(d==1)[0]; ends=np.where(d==-1)[0]-1
    seeds=[(int(s),int(e)) for s,e in zip(starts,ends) if e-s+1>=5]
    if not seeds: return np.zeros(len(hot_row), bool), []
    merged=[seeds[0]]
    for s,e in seeds[1:]:
        ls,le=merged[-1]
        if s-le-1<=2: merged[-1]=(ls,e)
        else: merged.append((s,e))
    m=np.zeros(len(hot_row), bool)
    for s,e in merged: m[s:e+1]=True
    return m, merged

mhw=np.zeros((NT,nsea), dtype=bool)
nruns=[]
for c in range(nsea):
    m,runs=cell_mhw(hot[:,c])
    mhw[:,c]=m
    if runs: nruns.append((c,runs))
print('cells with >=1 per-cell MHW:', len(nruns))
tot_segments=sum(len(r) for _,r in nruns)
print('total merged per-cell MHW segments:', tot_segments)

# ---- regional events
active=mhw.any(axis=1)
hp=np.concatenate(([False], active, [False]))
d=np.diff(hp.astype(np.int8))
starts=np.where(d==1)[0]; ends=np.where(d==-1)[0]-1
events=[(int(s),int(e)) for s,e in zip(starts,ends)]
print('active days:', int(active.sum()), 'of', NT)
print('regional events:', [(TGT[s].isoformat(), TGT[e].isoformat(), e-s+1) for s,e in events])
print('active pattern:', ''.join('#' if a else '.' for a in active))

np.savez_compressed('/work/results.npz', sea=sea, sea_idx=sea_idx, hot=hot, mhw=mhw,
                    thr_raw=thr_raw, clim_raw=clim_raw, thr_sm=thr_sm, clim_sm=clim_sm,
                    tgt_doy0=tgt_doy0)
print('total time', round(time.time()-t_start,1),'s')
