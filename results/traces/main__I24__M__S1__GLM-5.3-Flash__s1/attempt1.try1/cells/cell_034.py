import numpy as np, datetime as dt

thr=np.load('/tmp/thr.npy').reshape(366,60,60)
A=np.load('/tmp/A_all.npy'); ords=np.load('/tmp/dates_ord.npy')
dates=[dt.date.fromordinal(int(o)) for o in ords]
def doy_map(d):
    y=d.timetuple().tm_yday
    leap = d.year%4==0 and (d.year%100!=0 or d.year%400==0)
    return y if leap else (y+1 if y>=60 else y)
doy=np.array([doy_map(d) for d in dates])
ti=4540; tj=4631
print('doy range target:',doy[ti],doy[tj], dates[ti], dates[tj])
hot = A[ti:tj+1] >= thr[doy[ti:tj+1]]

def mhw_mask(hot, literal_order=True):
    T=hot.shape[0]
    m=np.zeros_like(hot)
    for i in range(hot.shape[1]):
        for j in range(hot.shape[2]):
            h=hot[:,i,j]
            if not h.any(): continue
            d=np.diff(np.concatenate(([0],h.view(np.int8),[0])))
            starts=np.where(d==1)[0]; ends=np.where(d==-1)[0]-1
            if literal_order:
                runs=[(s,e) for s,e in zip(starts,ends) if e-s+1>=5]
            else:
                runs=list(zip(starts,ends))
            if not runs: continue
            merged=[list(runs[0])]
            for s,e in runs[1:]:
                if s - merged[-1][1] - 1 <= 2:
                    merged[-1][1]=e
                else:
                    merged.append([s,e])
            for s,e in merged:
                if literal_order or (e-s+1>=5):
                    m[s:e+1,i,j]=True
    return m

m_lit=mhw_mask(hot,True)
m_std=mhw_mask(hot,False)
print('literal mask cell-days:',int(m_lit.sum()),' join-first mask cell-days:',int(m_std.sum()))
print('masks identical?',np.array_equal(m_lit,m_std))
diff=(m_lit!=m_std)
print('differing cell-days:',int(diff.sum()))

active_lit=m_lit.any(axis=(1,2)); active_std=m_std.any(axis=(1,2))
print('active days literal:',int(active_lit.sum()),' join-first:',int(active_std.sum()),' identical?',np.array_equal(active_lit,active_std))
