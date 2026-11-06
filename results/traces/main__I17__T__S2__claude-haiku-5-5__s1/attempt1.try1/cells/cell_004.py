
import pandas as pd
bt=pd.DatetimeIndex(b.time.values); tt=pd.DatetimeIndex(t.time.values)
bv=b.values.astype(np.float64); tv=t.values.astype(np.float64)
sea=np.all(np.isfinite(tv),axis=0)
print("sea cells:",sea.sum(), "target nan total:", np.isnan(tv).sum())
print("baseline nan per cell among sea:", np.isnan(bv[:,sea]).sum(axis=0).max() if sea.sum() else None)
print("baseline-years nan frac in region:", np.isnan(bv).mean())
def doy(d):
    # non-leap day of year mapping, 29 Feb = 60
    d=pd.DatetimeIndex(d)
    base=pd.to_datetime(dict(year=2001,month=d.month,day=np.where((d.month==2)&(d.day==29),28,d.day)))
    x=base.dayofyear.values.copy()
    leap29=(d.month==2)&(d.day==29)
    x[leap29]=60
    # for dates after Feb in leap years, base doy in 2001 is already correct as non-leap mapping
    return x
bdoy=doy(bt)
print(bt[:2], bdoy[:3], doy(pd.DatetimeIndex(['2004-02-29','2004-03-01','2004-12-31'])))
