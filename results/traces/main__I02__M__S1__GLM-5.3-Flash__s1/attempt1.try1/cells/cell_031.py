import numpy as np, datetime as dt
bdata=np.load('/tmp/baseline.npy', mmap_mode='r')
bdates=[dt.date(1991,12,27)+dt.timedelta(days=i) for i in range(bdata.shape[0])]
def doy_of(d):
    doy=(d-dt.date(d.year,1,1)).days+1
    return doy if (d.year%4==0 and (d.year%100!=0 or d.year%400==0)) or doy<60 else doy+1
bdoy=np.array([doy_of(d) for d in bdates])
inb=np.array([1992<=d.year<=2002 for d in bdates])
si,sj=40,40
def raw_for_doy(d):
    if d==60: return 0.5*(raw_for_doy(59)+raw_for_doy(61))
    donor=np.flatnonzero(inb&(bdoy==d))
    offs=sorted({min(max(i+k,0),len(bdates)-1) for i in donor for k in range(-5,6)})
    pool=np.asarray(bdata[offs])[:,si,sj].astype(np.float64)
    f2=np.sort(pool[np.isfinite(pool)]); n2=f2.size
    pos=n2*0.9-0.5; lo=int(np.floor(pos)); hi=int(np.ceil(pos)); g=pos-lo
    lo_c=min(max(lo,0),n2-1); hi_c=min(max(hi,0),n2-1)
    q2=f2[lo_c]+(f2[hi_c]-f2[lo_c])*g
    if g>=0.5: q2=f2[hi_c]-(f2[hi_c]-f2[lo_c])*(1.0-g)
    return q2
thr_sm=np.load('/tmp/thr_sm.npy'); clim_sm=np.load('/tmp/clim_sm.npy')
# recompute raw for all 366 doys (scalar loop) and smooth, compare
raw=np.array([raw_for_doy(d) for d in range(1,367)])
print("day60 raw:", raw[59], " vs mean(59,61):", 0.5*(raw[58]+raw[60]))
sm=np.array([raw[(np.arange(366)[:,None]+np.arange(-15,16)[None,:])%366].mean(axis=1)])[0]
for d in [1,60,153,200,214,244,366]:
    print(f"doy {d}: smoothed {sm[d-1]:.10f} pipeline {thr_sm[d-1,si,sj]:.10f} diff {abs(sm[d-1]-thr_sm[d-1,si,sj]):.2e}")
print("max diff all doys:", np.abs(sm-thr_sm[:,si,sj]).max())
