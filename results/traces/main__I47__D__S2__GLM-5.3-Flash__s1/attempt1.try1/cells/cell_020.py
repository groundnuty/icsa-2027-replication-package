import numpy as np, datetime as d2, xarray as xr
mhw = np.load('/work/mhw.npy')
thr_s = np.load('/work/thr_s.npy')
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
L0, L1, O0, O1 = 545, 604, 721, 780
sst_t = ds['analysed_sst'].isel(time=slice(13665,13757), latitude=slice(L0,L1+1), longitude=slice(O0,O1+1)).values.astype(np.float64)
tdates = [d2.date(2019,6,1)+d2.timedelta(days=i) for i in range(92)]
tdoy = np.array([d.timetuple().tm_yday for d in tdates])

def runs_of(hc):
    T=len(hc); out=[]; t=0
    while t<T:
        if hc[t]:
            u=t
            while u<T and hc[u]: u+=1
            out.append((t,u)); t=u
        else: t+=1
    return out

for cell in [(30,30),(15,15),(5,50),(0,0),(59,59)]:
    c0, c1 = cell
    sser = sst_t[:, c0, c1]                       # (92,)
    tser = thr_s[tdoy-1, c0, c1]                  # (92,)
    hc = sser >= tser
    rs = [r for r in runs_of(hc) if r[1]-r[0]>=5]
    mm=[]
    for r in rs:
        if mm and r[0]-mm[-1][1]<=2: mm[-1]=(mm[-1][0],r[1])
        else: mm.append(r)
    mask = np.zeros(92,np.uint8)
    for s,e in mm: mask[s:e]=1
    print('cell%s runs>=5:%2d merged:%d mask matches:%s intervals: %s' %
          (cell, len(rs), len(mm), bool((mask==mhw[:,c0,c1]).all()),
           [(str(tdates[s]), str(tdates[e-1])) for s,e in mm]))

active = mhw.reshape(92,-1).any(axis=1)
for o,e in [(5,21),(49,58)]:
    print('onset %s: active=%s (prev %s) | end %s: active=%s (next %s)' %
          (tdates[o], bool(active[o]), bool(active[o-1]), tdates[e], bool(active[e]),
           bool(active[e+1]) if e+1<92 else 'n/a'))
print('total active days:', int(active.sum()))
print('inactive days:', [str(tdates[i]) for i in range(92) if not active[i]])
