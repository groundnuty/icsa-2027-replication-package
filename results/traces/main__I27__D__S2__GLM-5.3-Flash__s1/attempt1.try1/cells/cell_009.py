import numpy as np, datetime

res = np.load('/work/mhw_result.npz')
mask = res['mask'].astype(bool).reshape(92,60,60); active = res['active']; tdays = res['tdays']
sea = res['sea']; lat = res['lat']; lon = res['lon']
print('active consistent:', bool((mask.any(axis=(1,2))==active).all()))

d = np.flatnonzero(np.diff(np.concatenate(([0], active.view(np.int8), [0]))))
starts = d[0::2]; ends = d[1::2]-1
for s,e in zip(starts,ends):
    print('event', str(tdays[s]), '->', str(tdays[e]), e-s+1, 'days')

# spot check a central sea cell independently
data = np.load('/work/region_data.npz'); sst = data['sst']; days=data['days']
thr = np.load('/work/clim.npz')['thr']
j,i = 30,30
assert sea[j,i]
tidx = np.where((days>=np.datetime64('2008-06-01'))&(days<=np.datetime64('2008-08-31')))[0]
sst_c = sst[tidx, j, i].astype(np.float64)
doys = np.array([datetime.date(2000,x.month,x.day).timetuple().tm_yday for x in days[tidx].tolist()])
thr_c = thr[doys-1, j*60+i]
hot_c = sst_c >= thr_c
evs=[]; k=0
while k < len(hot_c):
    if hot_c[k]:
        m=k
        while m+1<len(hot_c) and hot_c[m+1]: m+=1
        evs.append((k,m)); k=m+1
    else: k+=1
evs=[list(e) for e in evs if e[1]-e[0]+1>=5]
merged=[]
for e in evs:
    if merged and 1 <= e[0]-merged[-1][1]-1 <= 2 and not any(hot_c[g] for g in range(merged[-1][1]+1, e[0])):
        merged[-1]=[merged[-1][0], e[1]]
    else:
        merged.append(e)
print('cell (%.2f,%.2f) merged events:'%(lat[j],lon[i]), [(str(tdays[a]),str(tdays[b]),b-a+1) for a,b in merged])
mrows = np.where(mask[:,j,i])[0]
print('mask for that cell:', (str(tdays[mrows[0]]), str(tdays[mrows[-1]])) if len(mrows) else 'none', 'ndays', len(mrows))
# per-cell event count check: mask must equal union of merged events for this cell
expect = np.zeros(92, bool)
for a,b in merged: expect[a:b+1]=True
print('mask matches independent per-cell computation:', bool((expect==mask[:,j,i]).all()))
