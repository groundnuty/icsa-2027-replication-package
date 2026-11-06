import datetime as dt, calendar
# correct anchor generation: iterate actual days of baseline years
slot_anchors = {}
for y in range(1992, 2003):
    leap = calendar.isleap(y)
    d = dt.date(y, 1, 1)
    k = 1
    while d.year == y:
        s = (k+1) if k <= 59 else (0 if k == 60 else k)
        if s:
            slot_anchors.setdefault(s, []).append(d)
        d += dt.timedelta(days=1)
        k += 1
pool_window = {}
for s in range(1, 367):
    w = set()
    for d0 in slot_anchors.get(s, []):
        for off in range(-5, 6):
            w.add(d0 + dt.timedelta(days=off))
    pool_window[s] = sorted(w)
allw = set()
for s in range(1, 367): allw.update(pool_window[s])
print('overall range:', min(allw), max(allw), 'total distinct days:', len(allw))
sizes = [len(pool_window[s]) for s in range(1, 367)]
print('window sizes: min', min(sizes), 'max', max(sizes))
print('slot 1 window:', pool_window[1][0], pool_window[1][-1], len(pool_window[1]))
print('slot 2 window:', pool_window[2][0], pool_window[2][-1], len(pool_window[2]))
print('slot 60 window:', pool_window[60][0], pool_window[60][-1], len(pool_window[60]))
print('slot 61 window:', pool_window[61][0], pool_window[61][-1], len(pool_window[61]))
print('slot 366 window:', pool_window[366][0], pool_window[366][-1], len(pool_window[366]))
# every needed day present exactly in [1991-12-27, 2003-01-05]
need = []
d = dt.date(1991,12,27)
while d <= dt.date(2003,1,5):
    need.append(d); d += dt.timedelta(days=1)
print('needed days:', len(need), 'all in union:', all(x in allw for x in need))
