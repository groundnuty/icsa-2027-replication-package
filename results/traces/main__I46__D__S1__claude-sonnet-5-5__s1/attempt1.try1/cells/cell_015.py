import numpy as np,pandas as pd,glob
t=pd.DatetimeIndex(np.load('/work/t.npy'));fl=sorted(glob.glob('/work/c/*.nc'));e=pd.to_datetime([f[-11:-3] for f in fl])
m=np.where(t!=e)[0];print(len(m),t[m][:5],e[m][:5])