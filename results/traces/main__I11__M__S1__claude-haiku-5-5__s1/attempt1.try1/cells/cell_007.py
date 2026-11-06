
import numpy as np, pandas as pd, json, os, warnings
warnings.filterwarnings('ignore')
z=np.load('/tmp/w/sub.npz'); S=z['S']; dates=pd.DatetimeIndex(z['dates']); latv=z['lat']; lonv=z['lon']
# full baseline+window axis
B0=pd.Timestamp('1991-12-27'); B1=pd.Timestamp('2003-01-05')
Ax=pd.date_range(B0,B1)
Sb=S[:len(Ax)].astype(np.float64)  # first 4026 entries are 1991-12-27..2003-01-05 (sorted)
assert (dates[:len(Ax)]==Ax).all()
def doy(t):
    if t.month==2 and t.day==29: return 60
    nl=pd.Timestamp(year=2001,month=t.month,day=t.day).dayofyear  # non-leap doy
    return nl+1 if t.month>=3 else nl
doy_ax=np.array([doy(t) for t in Ax])
bmask=(Ax>=pd.Timestamp('1992-01-01'))&(Ax<=pd.Timestamp('2002-12-31'))
base_dates=Ax[bmask]
pool_idx={}
for dd in range(1,367):
    if dd==60: continue
    bs=base_dates[np.array([doy(t)==dd for t in base_dates])]
    if len(bs)==0: continue
    sel=set()
    for b in bs:
        for k in range(-5,6):
            sel.add(b+pd.Timedelta(days=k))
    idx=[(Ax.get_loc(t)) for t in sorted(sel) if t in Ax]
    pool_idx[dd]=np.array(idx)
print(len(pool_idx), min(len(v) for v in pool_idx.values()), max(len(v) for v in pool_idx.values()))
print(sorted(pool_idx)[:3], [doy(t) for t in [pd.Timestamp('2000-02-29'),pd.Timestamp('2001-03-01')]])
