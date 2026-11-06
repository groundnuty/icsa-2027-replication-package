import numpy as np, datetime as dt
m=np.load('/work/out/mhw.npy'); f=m.reshape(92,-1).mean(1)
d0=dt.date(2021,6,1)
for i in range(58,70): print(d0+dt.timedelta(i), round(float(f[i]),3), int(m[i].sum()))