
import fsspec, io, h5py, numpy as np
from datetime import date, timedelta

dat = np.load('/tmp/sst_data.npz')
master = dat['master']; target = dat['target']

# 1) verify time coordinate inside baseline files
fs = fsspec.filesystem('onedata')
BASE='/icsa2027_data_20261101T090944Z/s1z'
for name in ['sst_19920715.nc','sst_20021231.nc','sst_19911227.nc','sst_20030105.nc']:
    with fs.open(BASE+'/'+name,'rb') as f:
        h = h5py.File(io.BytesIO(f.read()),'r')
    print(name, "time coord:", h['time'][()][0].tobytes() if h['time'].dtype.kind in ('S','U') else h['time'][()])
    h.close()

# 2) regional mean SST curves
mean_master = np.nanmean(master, axis=(1,2))   # (4028,)
mean_target = np.nanmean(target, axis=(1,2))   # (92,)
j15_2021 = mean_target[(target_date0:=date(2021,6,1)) and 44]  # 2021-07-15 is day 44 (0-based: Jun1=0 -> Jul15 = 30+14 = 44)
print("2021-07-15 regional mean SST: %.3f K" % mean_target[44])
# baseline 15 July means over the 11 years
idx715 = [k for k,dt in enumerate([date(1991,12,27)+timedelta(days=i) for i in range(4028)]) if (dt.month,dt.day)==(7,15)]
print("baseline 15 Jul means:", np.round([mean_master[k] for k in idx715],3))

# 3) per-cell: 2021 summer max vs its baseline 90th pct (manual, all cells)
base_all = [date(1992,1,1)+timedelta(days=i) for i in range(4018)]
mdays=[31,29,31,30,31,30,31,31,30,31,30,31]; cum=[0]
for m in mdays: cum.append(cum[-1]+m)
doyf = lambda m,dd: cum[m-1]+dd
tgt_dates = [date(2021,6,1)+timedelta(days=i) for i in range(92)]

# for a few sample cells print: max 2021 summer SST & date, baseline p90 for that doy (hazen), and raw pool p90 linear
import warnings
worst = []
for ci in range(3600):
    i,k = np.unravel_index(ci,(60,60))
    s = target[:,i,k]
    if np.isnan(s).any(): continue
    m21 = np.nanmax(s); dtm = tgt_dates[int(np.nanargmax(s))]
    # baseline pool for doy(dtm)
    dd = doyf(dtm.month, dtm.day)
    b = [b for b in base_all if doyf(b.month,b.day)==dd]
    pool=[]
    for bb in b:
        for off in range(-5,6):
            t = bb+timedelta(days=off)
            if date(1991,12,27)<=t<=date(2003,1,5):
                pool.append(master[(t-date(1991,12,27)).days, i, k])
    pool=np.array(pool)
    q=np.nanquantile(pool,0.9,method='hazen')
    worst.append((m21-q, ci, dtm, m21, q))
worst.sort(reverse=True)
print("top 10 cells by (2021 max SST - baseline hazen p90 for that doy):")
for w in worst[:10]:
    print("  diff=%+.3f K cell=%d date=%s SST=%.2f thr=%.2f" % w)
print("best (max of these): %+.3f K" % worst[0][0])
print("how many cells have 2021 max >= p90:", sum(1 for w in worst if w[0]>=0))
