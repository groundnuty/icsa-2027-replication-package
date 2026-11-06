import numpy as np, datetime as dt, json, os
from scipy.ndimage import convolve1d
days=[]
d=dt.date(1991,12,27)
while d<=dt.date(2010,8,31):
    days.append(d); d+=dt.timedelta(1)
# load cache
S=[];LAT=None;LON=None
for dd in days:
    z=np.load(f'/work/cache/{dd.strftime("%Y%m%d")}.npz')
    S.append(z['sst'])
    if LAT is None: LAT=z['lat']; LON=z['lon']
    else:
        assert np.array_equal(LAT,z['lat']) and np.array_equal(LON,z['lon'])
S=np.stack(S)  # (N,60,60)
N=len(days); print(S.shape, N)
def doy(dd):
    return dt.date(2000,dd.month,dd.day).timetuple().tm_yday
D=np.array([doy(x) for x in days])
dates_arr=np.array(days)
base_mask=np.array([dt.date(1992,1,1)<=x<=dt.date(2002,12,31) for x in days])
targ_mask=np.array([dt.date(2010,6,1)<=x<=dt.date(2010,8,31) for x in days])
bidx=np.where(base_mask)[0]
pre_base=np.array([x<dt.date(1992,1,1) or x>dt.date(2002,12,31) for x in days])
# baseline-indicator for windows: baseline dates within the extended array (1991-12-27..2003-01-05) — use all dates in extended array
ext = np.array([dt.date(1991,12,27)<=x<=dt.date(2003,1,5) for x in days])
print(ext.sum(), base_mask.sum(), targ_mask.sum())