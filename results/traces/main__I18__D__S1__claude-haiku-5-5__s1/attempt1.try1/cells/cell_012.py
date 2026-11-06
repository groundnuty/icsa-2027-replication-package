import numpy as np, datetime as dt, json, os
from scipy.ndimage import convolve1d
days=[]
d=dt.date(1991,12,27)
while d<=dt.date(2003,1,5):
    days.append(d); d+=dt.timedelta(1)
d=dt.date(2010,6,1)
while d<=dt.date(2010,8,31):
    days.append(d); d+=dt.timedelta(1)
S=[];LAT=None;LON=None
for dd in days:
    z=np.load(f'/work/cache/{dd.strftime("%Y%m%d")}.npz')
    S.append(z['sst'])
    if LAT is None: LAT=z['lat']; LON=z['lon']
    else:
        assert np.array_equal(LAT,z['lat']) and np.array_equal(LON,z['lon'])
S=np.stack(S); N=len(days); print(S.shape)
def doy(dd): return dt.date(2000,dd.month,dd.day).timetuple().tm_yday
D=np.array([doy(x) for x in days])
base_mask=np.array([dt.date(1992,1,1)<=x<=dt.date(2002,12,31) for x in days])
targ_mask=np.array([dt.date(2010,6,1)<=x<=dt.date(2010,8,31) for x in days])
print(base_mask.sum(), targ_mask.sum())
# check Feb 28/29 and doy 366 counts
print(sorted(set(D[base_mask]))[:3], len(set(D[base_mask])))