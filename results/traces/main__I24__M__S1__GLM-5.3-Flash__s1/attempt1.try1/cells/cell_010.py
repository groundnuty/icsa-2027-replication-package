import numpy as np, datetime as dt
A=np.load('/tmp/A_all.npy'); ords=np.load('/tmp/dates_ord.npy')
dates=[dt.date.fromordinal(int(o)) for o in ords]
T=A.shape[0]; Aflat=A.reshape(T,-1)
def doy_map(d):
    y=d.timetuple().tm_yday
    leap = d.year%4==0 and (d.year%100!=0 or d.year%400==0)
    return y if leap else (y+1 if y>=60 else y)
doy=np.array([doy_map(d) for d in dates])
b0=dt.date(1992,1,1); b1=dt.date(2002,12,31)
base_idx=np.array([i for i,d in enumerate(dates) if b0<=d<=b1])
list_d={d: base_idx[doy[base_idx]==d] for d in range(1,367)}
offs=np.arange(-5,6)

thr_raw=np.load('/tmp/thr_raw.npy'); clim_raw=np.load('/tmp/clim_raw.npy')
# find a sea cell: finite at doy 152
fin_cells=np.isfinite(thr_raw[151])
sea_idx=np.where(fin_cells)[0]
print('n sea cells by finiteness:',len(sea_idx))
c=sea_idx[100]
# brute force check with numpy hazen for several (d, c)
rng=np.random.default_rng(0)
for d in [1,2,59,61,152,183,214,245,276,307,338,365,366]:
    P=Aflat[list_d[d][:,None]+offs[None,:], c]
    q_np=np.quantile(P[np.isfinite(P)],0.9,method='hazen') if np.isfinite(P).any() else np.nan
    m_np=np.nanmean(P)
    ok_q = (np.isnan(q_np) and np.isnan(thr_raw[d-1,c])) or np.isclose(q_np,thr_raw[d-1,c],rtol=0,atol=1e-12)
    ok_m = (np.isnan(m_np) and np.isnan(clim_raw[d-1,c])) or np.isclose(m_np,clim_raw[d-1,c],rtol=0,atol=1e-12)
    if not(ok_q and ok_m):
        print('MISMATCH',d,c,q_np,thr_raw[d-1,c],m_np,clim_raw[d-1,c])
print('brute-force spot checks passed')
# also check full all-NaN structure: NaNs only where cell is land
land=np.isnan(thr_raw[0])
print('land count:',land.sum(),'NaN rows all match land?',np.array_equal(np.isnan(thr_raw), land[None,:]))
