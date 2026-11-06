import numpy as np
Z = np.load("/tmp/mhw/loaded.npz"); Vt = Z["Vt"]
TC = np.load("/tmp/mhw/thrcli.npz"); THR = TC["THR"]
sea = np.isfinite(Vt).all(axis=0)   # (60,60)
print("sea cells:", sea.sum(), "of", sea.size)
print("thr NaN on sea cells:", np.isnan(THR[:, sea]).sum())
# any sea cell with NaN in thr?
bad = np.isnan(THR).any(axis=0) & sea
print("sea cells w/ any NaN thr:", bad.sum())
# sanity: compare a hand-computed hazen quantile for one cell/day
import datetime as dt
Vb = Z["Vb"]; BASE_START = dt.date(1991,12,27)
leap_month=[31,29,31,30,31,30,31,31,30,31,30,31]
doy_of={}
for m in range(1,13):
    s=1
    for mm in range(1,m): s+=leap_month[mm-1]
    for day in range(1,leap_month[m-1]+1): doy_of[(m,day)]=s+day-1
BL_START, BL_END = dt.date(1992,1,1), dt.date(2002,12,31)
bl_dates=[BL_START+dt.timedelta(days=i) for i in range((BL_END-BL_START).days+1)]
bl_ord=np.array([(dd.toordinal()-BASE_START.toordinal()) for dd in bl_dates])
bl_doy=np.array([doy_of[(dd.month,dd.day)] for dd in bl_dates])
d=172  # ~Jun 20
p=np.unique(bl_ord[bl_doy==d][:,None]+np.arange(-5,6)[None,:])
cell=(10,10)
vals=Vb[p,cell,cell[1]]  # careful: Vb[p, r, c]
vals=Vb[p, 10, 10]
fin=vals[np.isfinite(vals)]
hazen=np.nanquantile(vals,0.9,method="hazen")
# manual hazen (Hyndman-Fan type 5): h = (n+0.5)*p - 0.5 on sorted x (0-based)
x=np.sort(fin); n=len(x); pos=(n+0.5)*0.9-0.5
lo=int(np.floor(pos)); frac=pos-lo
manual = x[lo]*(1-frac)+x[lo+1]*frac if lo+1<n else x[-1]
print("hazen:",hazen,"manual:",manual,"match:",abs(hazen-manual)<1e-9,"n:",n,"finite:",np.isfinite(vals).sum())
print("THR[doy172] at (10,10) (pre-smooth?) using saved smoothed value:", THR[171,10,10])
