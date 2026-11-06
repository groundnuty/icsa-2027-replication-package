import numpy as np, datetime as dt
Z = np.load("/tmp/mhw/loaded.npz"); Vb = Z["Vb"]
BASE_START = dt.date(1991,12,27)
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

def check(d, r, c):
    p=np.unique(bl_ord[bl_doy==d][:,None]+np.arange(-5,6)[None,:])
    vals=Vb[p, r, c]
    hazen=np.nanquantile(vals,0.9,method="hazen")
    x=np.sort(vals[np.isfinite(vals)]); n=len(x)
    pos=(n+0.5)*0.9-0.5
    lo=int(np.floor(pos)); frac=pos-lo
    manual = x[lo]+(x[lo+1]-x[lo])*frac if lo+1<n else float(x[-1])
    mean=np.nanmean(vals)
    print(f"d={d} cell=({r},{c}) n={n}/{len(vals)} hazen={hazen:.6f} manual={manual:.6f} match={abs(hazen-manual)<1e-9} mean={mean:.6f}")

check(172, 10, 10)
check(1, 20, 20)
check(366, 30, 30)
check(61, 45, 55)
# also check pool dates for day 61 include Feb 29 values via Feb 28 windows
p61 = np.unique(bl_ord[bl_doy==61][:,None]+np.arange(-5,6)[None,:])
feb29s = [(BL_START+dt.timedelta(days=int(i))).isoformat() for i in p61 if (BL_START+dt.timedelta(days=int(i))).month==2 and (BL_START+dt.timedelta(days=int(i))).day==29]
print("Feb29 dates in W_61:", feb29s)
p59 = np.unique(bl_ord[bl_doy==59][:,None]+np.arange(-5,6)[None,:])
feb29s59 = [(BL_START+dt.timedelta(days=int(i))).isoformat() for i in p59 if (BL_START+dt.timedelta(days=int(i))).month==2 and (BL_START+dt.timedelta(days=int(i))).day==29]
print("Feb29 dates in W_59:", feb29s59)
