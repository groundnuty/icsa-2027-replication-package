import numpy as np, datetime as dt
def date_list(start, end):
    d = start; out=[]
    while d <= end:
        out.append(d); d += dt.timedelta(days=1)
    return out
base_dates = date_list(dt.date(1991,12,27), dt.date(2003,1,5))
base_idx = {x:i for i,x in enumerate(base_dates)}
base_arr = np.empty((4028,3600))
for i, dd in enumerate(base_dates):
    base_arr[i] = np.load(f"/work/region/{dd:%Y%m%d}.npy").ravel()

md = [31,29,31,30,31,30,31,31,30,31,30,31]; cum=[0]
for x in md: cum.append(cum[-1]+x)
def md_of(doy):
    for m in range(12):
        if cum[m] < doy <= cum[m+1]: return m+1, doy-cum[m]
def pool_for(d):
    m, day = md_of(d); s=set()
    for y in range(1992,2003):
        B = dt.date(y,m,day)
        for k in range(-5,6):
            T=B+dt.timedelta(days=k)
            if dt.date(1991,12,27)<=T<=dt.date(2003,1,5): s.add(base_idx[T])
    return np.array(sorted(s))

c = 5
idx59 = pool_for(59)
print("d=59 pool dates (first 3):", [base_dates[i] for i in idx59[:3]], "L=", len(idx59))
v = base_arr[idx59, c]
print("cell 5, d=59 pool: finite", np.isfinite(v).sum(), "of", len(v))
# which cells are NaN across d=59 pool?
fin = np.isfinite(base_arr[idx59,:]).all(axis=0)
print("cells fully finite for d=59 pool:", fin.sum())
# check a specific date
B = dt.date(1992,2,28)
i = base_idx[B]
print(base_dates[i], "finite count in that day:", np.isfinite(base_arr[i,:]).sum())
# sea mask
sea = np.load('/work/sea.npy')
print("cell 5 is sea:", sea[5], " cell 5 target finiteness already verified")
# check stored raw: recompute percentile
print("numpy hazen cell5 d59:", np.nanpercentile(base_arr[idx59,:].T,90,axis=1,method='hazen')[5])
