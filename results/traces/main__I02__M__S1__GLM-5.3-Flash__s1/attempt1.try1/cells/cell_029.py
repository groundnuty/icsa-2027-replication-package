import numpy as np, h5py, datetime as dt
D='/data/icsa2027_data_20261101T090944Z/s1z'
LI0,LJ0=34,213  # subregion origin in full domain
def dval(y,m,d, si=40,sj=40):
    with h5py.File(f'{D}/sst_{y}{m:02d}{d:02d}.nc','r') as f:
        return float(f['analysed_sst'][0,LI0+si,LJ0+sj])
def doy_of(d):
    doy=(d-dt.date(d.year,1,1)).days+1
    return doy if (d.year%4==0 and (d.year%100!=0 or d.year%400==0)) or doy<60 else doy+1

thr_sm=np.load('/tmp/thr_sm.npy'); clim_sm=np.load('/tmp/clim_sm.npy')
for (si,sj) in [(40,40),(10,10),(55,55),(0,0)]:
    for md in [(8,1),(6,1),(2,28)]:
        donors=[dt.date(y,*md) for y in range(1992,2003) if not (md==(2,29))]
        dates=sorted({dd+dt.timedelta(days=k) for dd in donors for k in range(-5,6)})
        vals=np.array([dval(x.year,x.month,x.day,si,sj) for x in dates])
        fin=np.sort(vals[np.isfinite(vals)])
        n=fin.size; pos=n*0.9-0.5; lo=int(np.floor(pos)); hi=int(np.ceil(pos)); g=pos-lo
        lo_c=min(max(lo,0),n-1); hi_c=min(max(hi,0),n-1)
        q=fin[lo_c]+(fin[hi_c]-fin[lo_c])*g
        if g>=0.5: q=fin[hi_c]-(fin[hi_c]-fin[lo_c])*(1.0-g)
        mean=fin.mean()
        ddoy=doy_of(dt.date(2004,*md))
        print(f"cell({si},{sj}) md={md}: n={n} brute q90={q:.6f} mean={mean:.6f} | pipeline thr_raw-ish thr_sm={thr_sm[ddoy-1,si,sj]:.4f} clim_sm={clim_sm[ddoy-1,si,sj]:.4f}")
