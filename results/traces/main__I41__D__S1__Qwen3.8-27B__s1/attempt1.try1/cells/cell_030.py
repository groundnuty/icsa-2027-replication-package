import numpy as np, pickle
from datetime import date

with open('/work/dates.pkl','rb') as f: dd = pickle.load(f)
tgt_dates = dd['tgt']; nb = len(dd['base'])
SST = np.load('/work/SST_all.npy')
sea = np.load('/work/sea_mask.npy').ravel()
thr_s = np.load('/work/thr_smooth.npy')

def mdoy(dt): return (date(2000, dt.month, dt.day) - date(2000,1,1)).days + 1
doys = np.array([mdoy(d) for d in tgt_dates])
tgt = SST[nb:].reshape(len(tgt_dates), 3600)
exc = tgt - thr_s[doys - 1]
exc_sea = exc[:, sea]
print("Jul 25 - Aug 31 daily max excess over threshold (K, sea cells):")
for i in range(55, 92):
    print(tgt_dates[i].isoformat(), round(float(np.nanmax(exc_sea[i])), 3))
