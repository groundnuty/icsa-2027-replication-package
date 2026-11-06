import numpy as np, datetime

res = np.load('/work/mhw_result.npz')
mask = res['mask'].astype(bool); active = res['active']; tdays = res['tdays']
print('active day count:', int(active.sum()), 'of', len(active))
print('inactive days:', [str(d) for d in tdays[~active]])
# masked cell-days vs hot cell-days
hot_total = 42370
print('masked cell-days:', int(mask.sum()), ' hot cell-days:', hot_total, ' gap days inside MHWs:', hot_total-int(mask.sum()))
# independent recheck: rebuild active from mask
act2 = mask.any(axis=(1,2))
print('active consistent:', bool((act2==active).all()))

# independent event detection (different code path)
d = np.flatnonzero(np.diff(np.concatenate(([0], active.view(np.int8), [0]))))
starts = d[0::2]; ends = d[1::2]-1
for s,e in zip(starts,ends):
    print('event', str(tdays[s]), '->', str(tdays[e]), e-s+1, 'days')

# spot-check one cell fully: print hot/evolution
data = np.load('/work/region_data.npz'); sst = data['sst']; days=data['days']
clim = np.load('/work/clim.npz'); thr = clim['thr']
sea = res['sea']
# pick a central sea cell
lat = data['lat']; lon = data['lon']
j,i = 30,30
while not sea[j,i]: j+=1
tidx = np.where((days>=np.datetime64('2008-06-01'))&(days<=np.datetime64('2008-08-31')))[0]
sst_c = sst[tidx, j, i].astype(np.float64)
doys = np.array([datetime.date(2000,d.month,d.day).timetuple().tm_yday for d in days[tidx].tolist()])
thr_c = thr[doys-1, j*60+i]
hot_c = sst_c >= thr_c
# naive per-cell events
evs=[]; k=0
while k < len(hot_c):
    if hot_c[k]:
        m=k
        while m+1<len(hot_c) and hot_c[m+1]: m+=1
        evs.append((k,m)); k=m+1
    else: k+=1
evs=[e for e in evs if e[1]-e[0]+1>=5]
# join gaps 1-2
merged=[]
for e in evs:
    if merged and 1 <= e[0]-merged[-1][1]-1 <= 2 and not any(hot_c[g] for g in range(merged[-1][1]+1, e[0])):
        merged[-1]=(merged[-1][0], e[1])
    else:
        merged.append(list(e) if isinstance(e,tuple) else e)
        merged[-1]=list(merged[-1])
print('cell(%d,%d) events:'%(j,i), [(str(tdays[a]),str(tdays[b]),b-a+1) for a,b in merged])
print('mask rows for that cell:', [(str(tdays[a]),str(tdays[b])) for a,b in zip(*np.where(mask[:,j,i]))] if mask[:,j,i].any() else 'none')
