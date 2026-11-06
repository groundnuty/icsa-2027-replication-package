import pandas as pd,numpy as np
z=np.load('/work/a.npz');B=z['B'].astype('f8');T=z['T'].astype('f8')
bd=pd.date_range('1991-12-27','2003-01-05')
m=(bd.month>=6)&(bd.month<=8)&(bd.year>=1992)&(bd.year<=2002)
sea=np.isfinite(T).all(0)
print(np.nanmean(B[m][:,sea]),np.nanmean(T[:,sea]),np.nanpercentile(B[m][:,sea],90))
print(np.nanmean(T[:,sea],1).max())