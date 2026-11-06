import numpy as np, datetime as dt

targ_sst = np.load('/work/targ_sst.npy'); thr_s = np.load('/work/thr_s.npy'); sea = np.load('/work/sea.npy')
mhw = np.load('/work/mhw.npy'); hot = np.load('/work/hot.npy')
targ_dates = [dt.date(2010,6,1) + dt.timedelta(days=i) for i in range(targ_sst.shape[0])]

def doy_map(d):
    leap = (d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0))
    return d.timetuple().tm_yday if (leap or d.month < 3) else d.timetuple().tm_yday + 1

doy_t = np.array([doy_map(d) for d in targ_dates])
thr_t = thr_s[doy_t - 1]
hot2 = np.where(np.isfinite(targ_sst), targ_sst >= thr_t, False)
print('hot identical:', np.array_equal(hot.astype(bool), hot2))

# independent per-cell MHW implementation via scanning state machine
mhw2 = np.zeros_like(mhw)
n_events_cell = 0
nt = targ_sst.shape[0]
for i in range(60):
    for j in range(60):
        if not sea[i,j]: continue
        h = hot2[:,i,j]
        # collect runs of hot
        runs = []
        t = 0
        while t < nt:
            if h[t]:
                u = t
                while u+1 < nt and h[u+1]: u += 1
                runs.append([t,u]); t = u+1
            else:
                t += 1
        # keep runs >= 5, join with gaps <= 2
        events = []
        for s,e in runs:
            if e-s+1 < 5: continue
            if events and s - events[-1][1] - 1 <= 2:
                events[-1][1] = e
            else:
                events.append([s,e])
        for s,e in events:
            mhw2[s:e+1, i, j] = 1
            n_events_cell += 1
print('per-cell MHWs (independent):', n_events_cell, '| mask identical:', np.array_equal(mhw, mhw2))

# independent regional event detection
active2 = mhw2.any(axis=(1,2))
active = mhw.any(axis=(1,2))
print('active identical:', np.array_equal(active, active2))
ev2 = []
t = 0
while t < nt:
    if active2[t]:
        u = t
        while u+1 < nt and active2[u+1]: u += 1
        ev2.append((targ_dates[t], targ_dates[u])); t = u+1
    else:
        t += 1
print('events independent:', ev2)
# day-by-day activity summary for context
for a,b in ev2:
    sub = active[np.datetime64(a - dt.date(2010,6,1), 'D') if False else (a - targ_dates[0]).days : (b - targ_dates[0]).days + 1]
    print('event', a, b, 'len', len(sub))
