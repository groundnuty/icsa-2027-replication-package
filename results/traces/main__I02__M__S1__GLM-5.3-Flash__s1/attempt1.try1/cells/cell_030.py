import numpy as np, h5py, datetime as dt
D='/data/icsa2027_data_20261101T090944Z/s1z'
LI0,LJ0=34,213
def dval(y,m,d,si,sj):
    with h5py.File(f'{D}/sst_{y}{m:02d}{d:02d}.nc','r') as f:
        return float(f['analysed_sst'][0,LI0+si,LJ0+sj])
def doy_of(d):
    doy=(d-dt.date(d.year,1,1)).days+1
    return doy if (d.year%4==0 and (d.year%100!=0 or d.year%400==0)) or doy<60 else doy+1

def brute(md, si, sj):
    donors=[dt.date(y,*md) for y in range(1992,2003)]
    dates=sorted({dd+dt.timedelta(days=k) for dd in donors for k in range(-5,6)})
    vals=np.array([dval(x.year,x.month,x.day,si,sj) for x in dates])
    fin=np.sort(vals[np.isfinite(vals)])
    n=fin.size; pos=n*0.9-0.5; lo=int(np.floor(pos)); hi=int(np.ceil(pos)); g=pos-lo
    lo_c=min(max(lo,0),n-1); hi_c=min(max(hi,0),n-1)
    q=fin[lo_c]+(fin[hi_c]-fin[lo_c])*g
    if g>=0.5: q=fin[hi_c]-(fin[hi_c]-fin[lo_c])*(1.0-g)
    return q, fin.mean(), n

thr_sm=np.load('/tmp/thr_sm.npy'); clim_sm=np.load('/tmp/clim_sm.npy')
# recompute raw for a small set of doys around Aug 1 to check both raw and smoothed
tdata=np.load('/tmp/target.npy'); sea=np.isfinite(tdata).all(axis=0)
cells=[(40,40),(55,55),(30,30),(2,40),(58,20)]
okraw=True; oksm=True
for (si,sj) in cells:
    assert sea[si,sj], (si,sj)
    for md in [(7,1),(8,1),(6,1),(2,28),(12,31),(1,1)]:
        d04=dt.date(2004,*md); ddoy=doy_of(d04)
        q,m,n=brute(md,si,sj)
        # raw pipeline for that doy: recompute via stored pool? quick recompute using /tmp/baseline.npy
        bdata=np.load('/tmp/baseline.npy', mmap_mode='r')
        bdates=[dt.date(1991,12,27)+dt.timedelta(days=i) for i in range(bdata.shape[0])]
        bdoy=np.array([doy_of(d) for d in bdates])
        inb=np.array([1992<=d.year<=2002 for d in bdates])
        donor=np.flatnonzero(inb&(bdoy==ddoy))
        offs=sorted({min(max(i+k,0),len(bdates)-1) for i in donor for k in range(-5,6)})
        pool=np.asarray(bdata[offs])[:,si,sj].astype(np.float64)
        f2=np.sort(pool[np.isfinite(pool)]); n2=f2.size
        pos=n2*0.9-0.5; lo=int(np.floor(pos)); hi=int(np.ceil(pos)); g=pos-lo
        lo_c=min(max(lo,0),n2-1); hi_c=min(max(hi,0),n2-1)
        q2=f2[lo_c]+(f2[hi_c]-f2[lo_c])*g
        if g>=0.5: q2=f2[hi_c]-(f2[hi_c]-f2[lo_c])*(1.0-g)
        m2=f2.mean()
        if not (np.isclose(q,q2) and np.isclose(m,m2)):
            okraw=False; print("RAW MISMATCH", (si,sj), md, q, q2, m, m2)
print("raw brute-force check across cells/doys:", okraw)

# smoothing check: recompute raw for doys 200..230 for cell(40,40), smooth, compare with thr_sm
si,sj=40,40
raws={}
for d in list(range(199,231))+list(range(1,17))+list(range(350,367)):
    if d==60: continue
    donor=np.flatnonzero(inb&(bdoy==d))
    offs=sorted({min(max(i+k,0),len(bdates)-1) for i in donor for k in range(-5,6)})
    pool=np.asarray(bdata[offs])[:,si,sj].astype(np.float64)
    f2=np.sort(pool[np.isfinite(pool)]); n2=f2.size
    pos=n2*0.9-0.5; lo=int(np.floor(pos)); hi=int(np.ceil(pos)); g=pos-lo
    lo_c=min(max(lo,0),n2-1); hi_c=min(max(hi,0),n2-1)
    q2=f2[lo_c]+(f2[hi_c]-f2[lo_c])*g
    if g>=0.5: q2=f2[hi_c]-(f2[hi_c]-f2[lo_c])*(1.0-g)
    raws[d]=q2
# build 366-array with day60 = mean(59,61)
d59=raws[59]; d61=raws[61]
raw_arr=np.full(366,np.nan)
for d,v in raws.items(): raw_arr[d-1]=v
raw_arr[59]=0.5*(raw_arr[58]+raw_arr[60])
sm=np.array([raw_arr[(np.arange(366)[:,None]+np.arange(-15,16)[None,:])%366].mean(axis=1)])[0]
for d in [200,214,214,225,153,244,1,5,360]:
    a=sm[d-1]; b=thr_sm[d-1,si,sj]
    print(f"doy {d}: recomputed smoothed {a:.10f}  pipeline {b:.10f}  diff {abs(a-b):.2e}")
