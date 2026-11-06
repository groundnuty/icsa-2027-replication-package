import pickle,numpy as np,pandas as pd
dates,res=pickle.load(open('/tmp/cache.pkl','rb'))
S=np.stack([r[1] for r in res]).astype('float64');dates=pd.DatetimeIndex(dates)
nb=(dates<='2003-01-05').sum();B=S[:nb];T=S[nb:]
sea=np.isfinite(T).all(0)
bd=dates[:nb]
# simple check: July 15 climatology 90th pct
m=(bd.month==7)&(bd.day>=10)&(bd.day<=20)&(bd.year>=1992)&(bd.year<=2002)
print(np.nanmean(np.nanquantile(B[m][:,sea],0.9,axis=0)), np.nanmean(T[(dates[nb:].month==7)][:,sea]))
print(np.nanmean(B[m][:,sea]))