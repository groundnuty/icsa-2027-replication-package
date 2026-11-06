import numpy as np, datetime, json

data = np.load('/work/region_data.npz')
sst = data['sst']; days = data['days']; lat = data['lat']; lon = data['lon']
clim = np.load('/work/clim.npz')
thr = clim['thr']  # (366, 3600)

# target days
tmask = (days >= np.datetime64('2008-06-01')) & (days <= np.datetime64('2008-08-31'))
tidx = np.where(tmask)[0]
tdays = days[tidx]
NT = len(tdays)
print('target days', NT, tdays[0], tdays[-1])

sst_t = sst[tidx].astype(np.float64)          # (92, 60, 60)
sea = np.isfinite(sst_t).all(axis=0)          # finite every target day
print('sea cells:', int(sea.sum()), 'of', sea.size)

doys_t = np.array([datetime.date(2000, d.month, d.day).timetuple().tm_yday for d in tdays.tolist()])
thr_t = thr[doys_t - 1]                       # (92, 3600)
flat_t = sst_t.reshape(NT, -1)
hot = flat_t >= thr_t                         # hot: SST >= threshold
hot[:, ~sea.ravel()] = False                  # land: never hot
print('hot days total:', int(hot.sum()))

def cell_events(hotvec):
    """runs of >=5 hot days, then chain-join across gaps of 1-2 all-non-hot days."""
    n = len(hotvec)
    ev = []
    i = 0
    while i < n:
        if hotvec[i]:
            j = i
            while j+1 < n and hotvec[j+1]: j += 1
            ev.append([i, j])
            i = j+1
        else:
            i += 1
    ev = [e for e in ev if e[1]-e[0]+1 >= 5]
    # merge: adjacent events with 1-2 days strictly between, all non-hot
    changed = True
    ambiguous = 0
    while changed and len(ev) > 1:
        changed = False
        for k in range(len(ev)-1):
            a, b = ev[k], ev[k+1]
            gap = list(range(a[1]+1, b[0]))
            if 1 <= len(gap) <= 2 and not any(hotvec[g] for g in gap):
                ev[k] = [a[0], b[1]]
                del ev[k+1]
                changed = True
                break
    return ev

mask = np.zeros_like(hot, dtype=bool)
n_events = 0; lens = []; ambiguous_cases = 0
for c in range(hot.shape[1]):
    if not sea.ravel()[c]: continue
    ev = cell_events(hot[:, c])
    n_events += len(ev)
    for a, b in ev:
        lens.append(b-a+1)
        mask[a:b+1, c] = True
print('per-cell MHWs:', n_events, 'len min/med/max:', min(lens), int(np.median(lens)), max(lens))
print('cells with >=1 MHW:', int((mask.any(axis=0)).sum()))

# check for potential ambiguous configs: MHWs separated by <=2 days where gap contains a hot (short-run) day
def check_ambiguous(hotvec):
    n=len(hotvec); ev=[]; i=0
    while i < n:
        if hotvec[i]:
            j=i
            while j+1<n and hotvec[j+1]: j+=1
            ev.append([i,j]); i=j+1
        else: i+=1
    ev=[e for e in ev if e[1]-e[0]+1>=5]
    for k in range(len(ev)-1):
        gap=list(range(ev[k][1]+1, ev[k+1][0]))
        if 1<=len(gap)<=2 and any(hotvec[g] for g in gap):
            return True
    return False
amb = sum(check_ambiguous(hot[:,c]) for c in range(hot.shape[1]) if sea.ravel()[c])
print('ambiguous gap cases (hot short-run inside 1-2 day separation):', amb)

active = mask.any(axis=1)
# regional events = maximal runs of consecutive active days
events = []
i = 0
while i < NT:
    if active[i]:
        j = i
        while j+1 < NT and active[j+1]: j += 1
        events.append((i, j)); i = j+1
    else:
        i += 1
print('regional events:', len(events))
for a,b in events:
    print(' ', str(tdays[a]), '->', str(tdays[b]), f'({b-a+1} days)')

np.savez_compressed('/work/mhw_result.npz', mask=mask.astype(np.uint8), active=active,
                    tdays=tdays, sea=sea, lat=lat, lon=lon)
