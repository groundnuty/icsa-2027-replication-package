
bt=pd.DatetimeIndex(b.time.values); tt=pd.DatetimeIndex(t.time.values)
print(bt[0],bt[-1],len(bt), bt.is_unique, tt[0],tt[-1],len(tt))
bv=b.values.astype(np.float64); tv=t.values.astype(np.float64)
sea=np.isfinite(tv).all(axis=0)
print('sea cells',sea.sum(),'of',sea.size, 'nan-all baseline cells', (~np.isfinite(bv).any(axis=0)).sum())
print('target nan count per cell range', np.isnan(tv).sum(axis=0).min(), np.isnan(tv).sum(axis=0).max())
# day-of-year via leap calendar
def doy(d): return pd.Timestamp(2000,d.month,d.day).dayofyear
# full daily date index for baseline extended range
dates=pd.date_range('1991-12-27','2003-01-05')
idx={d:i for i,d in enumerate(bt)}
assert len(dates)==len(bt)
