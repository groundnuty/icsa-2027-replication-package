
import numpy as np, datetime as dt, json, os
z=np.load('/tmp/sub.npz')
S=z['S']; lat=z['lat']; lon=z['lon']; dates=[dt.date.fromisoformat(s) for s in z['dates']]
idx={d:i for i,d in enumerate(dates)}
def doy(d):
    # 1 Jan=1 ... 29 Feb=60 (leap), 1 Mar=61 ; non-leap 1 Mar=60? spec: 1 Mar =61 always
    leap = (d.year%4==0 and (d.year%100!=0 or d.year%400==0))
    base_doy = (dt.date(2001,d.month,d.day)-dt.date(2001,1,1)).days+1 if not (d.month==2 and d.day==29) else 60
    if d.month==2 and d.day==29: return 60
    # non-leap calendar mapping: days after Feb 28 get +1 (so Mar 1=61 in both years)
    if d.month>2: return (dt.date(2001,d.month,d.day)-dt.date(2001,1,1)).days+2
    return base_doy
# check mapping
assert doy(dt.date(1992,2,28))==59 and doy(dt.date(1992,2,29))==60 and doy(dt.date(1992,3,1))==61 and doy(dt.date(1992,12,31))==366 and doy(dt.date(1993,12,31))==366-0 or True
print(doy(dt.date(1993,12,31)), doy(dt.date(1992,12,31)), doy(dt.date(1993,3,1)), doy(dt.date(1992,3,1)))
# pools: per doy d != 60, set of calendar dates within +-5 of baseline dates with that doy
baseline=[dt.date(1992,1,1)+dt.timedelta(i) for i in range((dt.date(2002,12,31)-dt.date(1992,1,1)).days+1)]
pool_dates={d:set() for d in range(1,367) if d!=60}
for b in baseline:
    k=doy(b)
    if k==60: continue
    for off in range(-5,6):
        pool_dates[k].add(b+dt.timedelta(off))
print({k:len(v) for k,v in list(pool_dates.items())[:3]})
thr=np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
for k,ds_ in pool_dates.items():
    arr=np.stack([S[idx[x]] for x in sorted(ds_) if x in idx])  # all dates present?
    assert len([x for x in ds_ if x in idx])==len(ds_)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        thr[k]=np.nanquantile(arr,0.9,axis=0,method='hazen')
        clim[k]=np.nanmean(arr,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):  # a: (367,...) index 1..366 used; circular on 366
    b=a[1:367]
    out=np.zeros_like(b)
    for s in range(-15,16):
        out+=np.roll(b,-s,axis=0)
    out/=31
    res=np.full_like(a,np.nan); res[1:367]=out; return res
thrS=smooth(thr); climS=smooth(clim)
print(np.isnan(thrS[1:367]).sum(), np.isnan(thrS[1:367][:, :]).sum())
