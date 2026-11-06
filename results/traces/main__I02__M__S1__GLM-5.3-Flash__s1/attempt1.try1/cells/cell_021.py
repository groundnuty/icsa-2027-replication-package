import numpy as np, datetime as dt, h5py, os
D='/data/icsa2027_data_20261101T090944Z/s1z'

def dval(y,m,d, i=40,j=40):
    with h5py.File(f'{D}/sst_{y}{m:02d}{d:02d}.nc','r') as f:
        return float(f['analysed_sst'][0,i,j])

# brute force for cell (40,40), doy of Aug 1 = 214 (leap), and Jun 1 -> 153
def doy_of(d):
    doy=(d-dt.date(d.year,1,1)).days+1
    return doy if (d.year%4==0 and (d.year%100!=0 or d.year%400==0)) or doy<60 else doy+1

for target_md in [(8,1),(6,1),(2,28)]:
    # donors: same month/day in each baseline year 1992..2002 (29 Feb only in leap years)
    donors=[]
    for y in range(1992,2003):
        try:
            donors.append(dt.date(y,*target_md))
        except ValueError:
            pass
    dates=set()
    for dd in donors:
        for k in range(-5,6):
            dates.add(dd+dt.timedelta(days=k))
    dates=sorted(dates)
    vals=np.array([dval(x.year,x.month,x.day) for x in dates])
    fin=vals[np.isfinite(vals)]
    n=fin.size; pos=n*0.9-0.5; lo=int(np.floor(pos)); hi=int(np.ceil(pos)); g=pos-lo
    lo_c=min(max(lo,0),n-1); hi_c=min(max(hi,0),n-1)
    q=fin[lo_c]+(fin[hi_c]-fin[lo_c])*g
    if g>=0.5: q=fin[hi_c]-(fin[hi_c]-fin[lo_c])*(1.0-g)
    mean=fin.mean()
    ddoy=doy_of(dt.date(2004,*target_md))
    thr_sm=np.load('/tmp/thr_sm.npy'); clim_sm=np.load('/tmp/clim_sm.npy')
    # brute-force smooth: raw for this doy +/- 15 (mod 366) from saved raw? recompute raw for neighbours quickly
    print(f"md={target_md} doy2004={ddoy}: n_dates={len(dates)} n_finite={n} brute q90={q:.6f} mean={mean:.6f}")
    print(f"   pipeline (before smoothing check) thr_sm={thr_sm[ddoy-1,40,40]:.6f} clim_sm={clim_sm[ddoy-1,40,40]:.6f}")
