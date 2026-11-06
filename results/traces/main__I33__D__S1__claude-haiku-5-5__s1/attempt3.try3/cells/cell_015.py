import numpy as np, datetime, json, os
z=np.load('/work/region.npz')
dates=np.array([datetime.date.fromisoformat(s) for s in z['dates']]); sst=z['sst']; LAT=z['lat']; LON=z['lon']
def doy_of(d):
    # 1-based day-of-year with leap-year numbering: Feb29=60 always
    leap = (d.year%4==0 and (d.year%100!=0 or d.year%400==0))
    base=datetime.date(2001,d.month,d.day) if not(d.month==2 and d.day==29) else None
    if base is None: return 60
    # map non-leap numbering: days before month + day, with leap shift
    dd=(datetime.date(d.year,d.month,d.day)-datetime.date(d.year,1,1)).days+1
    if leap and dd>=60: dd+=0  # dd already counts Feb 29 as day 60 in leap years
    else:
        if not leap and dd>=60: dd+=1  # non-leap: Mar1=61
    return dd
# simpler explicit mapping: doy with Feb29=60; non-leap Mar1 =61
def doy(d):
    leap = (d.year%4==0 and (d.year%100!=0 or d.year%400==0))
    if d.month==2 and d.day==29: return 60
    dd=(d-datetime.date(d.year,1,1)).days+1
    if not leap and dd>=60: dd+=1
    return dd
assert doy(datetime.date(1992,2,28))==59 and doy(datetime.date(1992,3,1))==61 and doy(datetime.date(1992,12,31))==366 and doy(datetime.date(1993,12,31))==365 and doy(datetime.date(1993,3,1))==61
# pools
idx_of={d:i for i,d in enumerate(dates)}
base_start=datetime.date(1992,1,1); base_end=datetime.date(2002,12,31)
bdays=[d for d in dates if base_start<=d<=base_end]
pools={k:set() for k in range(1,367) if k!=60}
for b in dates:
    if not (base_start<=b<=base_end): continue
    k=doy(b)
    if k==60: continue
    for off in range(-5,6):
        pools[k].add(b+datetime.timedelta(off))
print('baseline pool days min/max', min(pools), max(pools), [len(pools[k]) for k in (1,59,61,366)])
ncell=sst.shape[1:]
thr=np.full((367,)+ncell,np.nan); clim=np.full((367,)+ncell,np.nan)
for k in range(1,367):
    if k==60: continue
    ii=[idx_of[d] for d in pools[k] if d in idx_of]
    vals=sst[ii]  # (n,lat,lon)
    with np.errstate(all='ignore'):
        thr[k]=np.nanquantile(vals,0.9,axis=0,method='hazen') if True else None
        clim[k]=np.nanmean(vals,axis=0)
print('pool sizes used', len([d for d in pools[1] if d in idx_of]))