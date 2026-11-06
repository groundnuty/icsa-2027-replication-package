
import json, os
os.makedirs('output',exist_ok=True)
# day-of-year mapping (fixed calendar)
def doy(ts):
    cum=[0,31,59,91,121,152,182,213,244,274,305,335]  # Jan..Dec start offsets for leap-year layout
    out=[]
    for d in ts:
        if d.month==2 and d.day==29: out.append(60)
        else:
            m=d.month; base=cum[m-1]+d.day
            if m>2: base+=1  # leap layout: March 1 = 61
            out.append(base)
    return np.array(out)
dext = pd.DatetimeIndex(t)
D = doy(dext)
print(D[:3], D[dext==pd.Timestamp('2000-02-29')], D[dext==pd.Timestamp('2001-03-01')], D[dext==pd.Timestamp('2001-12-31')])
base_mask_centres = (dext>=pd.Timestamp('1992-01-01'))&(dext<=pd.Timestamp('2002-12-31'))
centre_idx = np.where(base_mask_centres)[0]
ndates=len(dext)
# per d: pool index mask (union over centres with doy d of window +-5 days)
thr = np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
pool_sizes={}
for d in range(1,367):
    if d==60: continue
    cs = centre_idx[D[centre_idx]==d]
    if len(cs)==0: continue
    m = np.zeros(ndates,bool)
    for c in cs:
        lo_i=c-5; hi_i=c+5
        # dates within calendar +-5 days (time index is contiguous daily)
        m[max(lo_i,0):min(hi_i,ndates-1)+1]=True
    # check contiguity of data dates
    pool=A[m]
    pool_sizes[d]=pool.shape[0]
    thr[d]=np.quantile(pool,0.9,axis=0,method='hazen')
    clim[d]=pool.mean(axis=0)
print(sorted(pool_sizes.items())[:3], sorted(pool_sizes.items())[-3:], min(pool_sizes.values()), max(pool_sizes.values()))
