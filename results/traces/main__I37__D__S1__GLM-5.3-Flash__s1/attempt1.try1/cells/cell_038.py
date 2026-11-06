import numpy as np, datetime as dt

sst = np.load('/work/sst_cube.npy')
sea = np.load('/work/sea_mask.npy')
thr_u = np.load('/work/thr_unsmoothed.npy')
clim_u = np.load('/work/clim_unsmoothed.npy')
NB = 4027

CUM = [31,29,31,30,31,30,31,31,30,31,30,31]
def dayofyear(d): return sum(CUM[:d.month-1]) + d.day

dates_all = [dt.date(1991,12,27)+dt.timedelta(days=k) for k in range(NB)]
doys_all = np.array([dayofyear(d) for d in dates_all])
yrs_all = np.array([d.year for d in dates_all])
base_pos = np.where((yrs_all>=1992)&(yrs_all<=2002))[0]
base_doys = doys_all[base_pos]
sea_flat_idx = np.where(sea.ravel())[0]

# take first sea cell (flat idx) -> 2D coords
fidx = sea_flat_idx[0]
jr, ic = divmod(int(fidx), 61)
print("cell 2D:", (jr, ic))
c = 0  # its column in the flat-sea array

d = 213
w = (((d-1+np.arange(-5,6)) % 366) + 1)
idx = base_pos[np.isin(base_doys, w)]
vals = sst[np.ix_(idx, np.arange(jr, jr+1), np.arange(ic, ic+1))][:,0,0]
print("pool size:", len(vals))
sv = np.sort(vals)
n = len(sv)
print("mean:", sv.mean().round(3), "std:", sv.std(ddof=0).round(3))
# hazen q90: positions p_i = (i+0.5)/n
import math
pos = 0.9
h = pos*(n+1)-0.5
lo = int(math.floor(h)); frac = h - lo
q = sv[lo] + frac*(sv[min(lo+1,n-1)]-sv[lo])
print("manual hazen q90:", round(q,3))
print("numpy hazen q90:", round(np.nanquantile(vals, 0.9, method='hazen'),3))
print("stored thr_u:", round(thr_u[d-1, c],3), "stored clim_u:", round(clim_u[d-1, c],3))
print("pool top values:", sv[int(n*0.88):].round(2))
# Aug 1 values across baseline years, this cell
for y in range(1992, 2003):
    k = dates_all.index(dt.date(y,8,1))
    print(y, round(float(sst[k, jr, ic]),2))
