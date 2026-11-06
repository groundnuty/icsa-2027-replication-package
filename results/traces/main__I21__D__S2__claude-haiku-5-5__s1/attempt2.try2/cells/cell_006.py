
import datetime as dtm
# day-of-year: leap-year calendar (year 2000)
def doy_of(dates):
    return np.array([ (d.replace(year=2000)).timetuple().tm_yday for d in dates ])
Tdt = T.to_pydatetime()
D = doy_of(Tdt)
base_s, base_e = pd.Timestamp('1992-01-01'), pd.Timestamp('2002-12-31')
Tpd = pd.DatetimeIndex(T)
isbase = (Tpd>=base_s)&(Tpd<=base_e)
Dbase = D.copy()
# all dates within window: 1991-12-27 .. 2003-01-05 -> index array of T
inwin = (Tpd>=pd.Timestamp('1991-12-27'))&(Tpd<=pd.Timestamp('2003-01-05'))
assert inwin.sum()==(pd.Timestamp('2003-01-05')-pd.Timestamp('1991-12-27')).days+1
thr_raw = np.full((367,60,60), np.nan); clim_raw=np.full((367,60,60), np.nan)
bidx = np.where(isbase)[0]
for d in range(1,367):
    if d==60: continue
    bdates = bidx[D[bidx]==d]
    # union of windows ±5 days
    wdates=set()
    for bi in bdates:
        for k in range(-5,6):
            wdates.add(bi+k)
    widx = np.array(sorted(wdates))
    # keep only indices within the loaded time array (should be all)
    assert widx.min()>=0 and widx.max()<len(T)
    pool = A[widx]
    with np.errstate(all='ignore'):
        thr_raw[d] = np.nanpercentile(pool, 90, axis=0, method='hazen')
        clim_raw[d] = np.nanmean(pool, axis=0)
thr_raw[60]=(thr_raw[59]+thr_raw[61])/2; clim_raw[60]=(clim_raw[59]+clim_raw[61])/2
thr_raw=thr_raw[1:]; clim_raw=clim_raw[1:]   # 366 entries, index d-1
def smooth(x):
    out=np.empty_like(x)
    for i in range(366):
        idx=[(i+k)%366 for k in range(-15,16)]
        out[i]=x[idx].mean(axis=0)
    return out
thr=smooth(thr_raw); clim=smooth(clim_raw)
sea = np.all(np.isfinite(A[(Tpd>=pd.Timestamp('2021-06-01'))&(Tpd<=pd.Timestamp('2021-08-31'))]),axis=0)
print('sea cells', sea.sum(), 'of', sea.size)
print('NaN thr in sea cells', np.isnan(thr[:,sea]).sum(), 'NaN clim', np.isnan(clim[:,sea]).sum())
print('NaN raw thr sea', np.isnan(thr_raw[:,sea]).sum())
