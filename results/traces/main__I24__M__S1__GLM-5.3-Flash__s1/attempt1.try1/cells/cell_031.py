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
base_doy=doy[base_idx]
list_d={d: base_idx[base_doy==d] for d in range(1,367)}
offs=np.arange(-5,6)
thr_raw=np.load('/tmp/thr_raw.npy'); clim_raw=np.load('/tmp/clim_raw.npy')
# find sea cells
land = np.isnan(A).all(axis=0).reshape(-1)
sea_cells=np.where(~land)[0]
print('sea cells:',len(sea_cells))
c=int(sea_cells[500])
# brute-force verify with np.nanquantile over several doys
for d in [1,2,59,60,61,90,152,183,214,245,276,307,338,365,366]:
    P=Aflat[list_d[d][:,None]+offs[None,:], c].ravel()
    fin=np.isfinite(P)
    q_ref=np.nanquantile(P,0.9,method='hazen') if fin.any() else np.nan
    m_ref=np.nanmean(P) if fin.any() else np.nan
    tq=thr_raw[d-1,c]; tm=clim_raw[d-1,c]
    qok=(tq==q_ref) if not np.isnan(q_ref) else np.isnan(tq)
    mok=(tm==m_ref) if not np.isnan(m_ref) else np.isnan(tm)
    print(d, 'q match:',qok, 'm match:',mok, 'thr %.6f clim %.6f'%(tq,tm))
