import numpy as np, xarray as xr, json, os, datetime as dtt

mhw = np.load('/work/mhw.npy')
thr_s = np.load('/work/thr_s.npy')
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
L0, L1, O0, O1 = 545, 604, 721, 780
sst_t = ds['analysed_sst'].isel(time=slice(13665,13757), latitude=slice(L0,L1+1), longitude=slice(O0,O1+1)).values.astype(np.float64)
sst_b_all = np.load('/work/sst_b.npy')
B0 = dtt.date(1991,12,27); B1 = dtt.date(2003,1,5)
bdates = [B0 + dtt.timedelta(days=i) for i in range((B1-B0).days+1)]
def doy_of(d): return d.timetuple().tm_yday

def raw_thr_for_doy_onecell(tgt, cell):  # independent, pure-python, single cell
    vals = []
    for bd in bdates:
        if doy_of(bd) == tgt:
            for k in range(-5,6):
                q = bd + dtt.timedelta(days=k)
                if B0 <= q <= B1:
                    vals.append(sst_b_all[(q-B0).days, cell[0], cell[1]])
    v = np.sort(np.array(vals, float)); v = v[np.isfinite(v)]
    n = len(v)
    if n == 0: return np.nan
    h = n*0.9 - 0.5; lo = int(np.floor(h)); hi = int(np.ceil(h))
    lo = min(lo, n-1); hi = min(hi, n-1)
    return v[lo] + (h-lo)*(v[hi]-v[lo])

# independent rebuild of smoothed threshold for doy 205 (2019-07-24) at cells (30,30) and (10,10)
for cell in [(30,30),(10,10)]:
    raws = {d: raw_thr_for_doy_onecell(d, cell) for d in range(190, 221)}
    expl = np.mean([raws[d] for d in range(190,221)])
    got = thr_s[204, cell[0], cell[1]]
    print('cell%s doy205: independent=%.6f thr_s=%.6f diff=%.2e' % (cell, expl, got, abs(expl-got)))

# independent per-cell MHW check for 3 sample cells (one per event + one big cell)
def runs_of(hc):
    T=len(hc); out=[]; t=0
    while t<T:
        if hc[t]:
            u=t
            while u<T and hc[u]: u+=1
            out.append((t,u)); t=u
        else: t+=1
    return out
import datetime as d2
T0 = d2.date(2019,6,1)
for cell in [(30,30),(15,15),(5,50)]:
    hc = (sst_t[:,cell[0],cell[1]] >= thr_s[np.array([d2.date(2019,6,1)+d2.timedelta(days=i) for i in range(92)], dtype='datetime64[D]').astype(object)] ).tolist()
    hc = [bool(x) for x in hc]
    rs = [r for r in runs_of(hc) if r[1]-r[0]>=5]
    mm=[]
    for r in rs:
        if mm and r[0]-mm[-1][1]<=2: mm[-1]=(mm[-1][0],r[1])
        else: mm.append(r)
    mask = np.zeros(92,np.uint8)
    for s,e in mm: mask[s:e]=1
    same = bool((mask == mhw[:,cell[0],cell[1]]).all())
    print('cell%s runs>=5: %d merged: %s  mask matches: %s  intervals: %s' %
          (cell, len(rs), len(mm), same, [(str(T0+d2.timedelta(days=s)), str(T0+d2.timedelta(days=e-1))) for s,e in mm]))

# event boundary verification: active on onset days, inactive the day before each onset and after each end
active = mhw.reshape(92,-1).any(axis=1)
onsets = [5, 49]; ends = [21, 58]  # indices: 06-06, 07-20; 06-22, 07-29
for o,e in zip(onsets, ends):
    print('onset %s active=%s, day-before active=%s | end %s active=%s, day-after active=%s' %
          (str(T0+d2.timedelta(days=o)), bool(active[o]), bool(active[o-1]),
           str(T0+d2.timedelta(days=e)), bool(active[e]), bool(active[e+1]) if e+1<92 else 'n/a'))
print('total active days:', int(active.sum()))
