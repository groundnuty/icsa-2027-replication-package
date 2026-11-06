import datetime as dt, calendar, json, os
CUM = None
def doy_map(d):
    # day of year 1..366: 1 Jan=1, 28 Feb=59, 29 Feb=60 (leap only), 1 Mar=61, 31 Dec=366
    k = d.timetuple().tm_yday
    if calendar.isleap(d.year):
        return k
    return k if k <= 59 else k + 1
# verify exhaustively
for y in [1992,1993,1996,2000,2001,2004]:
    day = 0
    ok = True
    d = dt.date(y,1,1)
    while d.year == y:
        day += 1
        if doy_map(d) != day:
            print('MISMATCH', d, doy_map(d), day); ok = False
        d += dt.timedelta(days=1)
    print(y, 'ok', ok, 'Dec31 ->', doy_map(dt.date(y,12,31)))
# anchors: baseline dates grouped by mapped doy
slot_anchors = {}
for y in range(1992, 2003):
    d = dt.date(y,1,1)
    while d.year == y:
        slot_anchors.setdefault(doy_map(d), []).append(d)
        d += dt.timedelta(days=1)
print('slots with anchors:', len(slot_anchors), 'slot 60 has anchors:', slot_anchors.get(60, [])[:3])
print('anchors per slot (typical):', len(slot_anchors[1]), len(slot_anchors[61]), len(slot_anchors[366]))
pool_window = {}
for s in range(1, 367):
    w = set()
    for d0 in slot_anchors.get(s, []):
        for off in range(-5, 6):
            w.add(d0 + dt.timedelta(days=off))
    pool_window[s] = sorted(w)
allw = set()
for s in range(1, 367): allw.update(pool_window[s])
print('overall union range:', min(allw), max(allw), 'total distinct days:', len(allw))
sizes = [len(pool_window[s]) for s in range(1, 367)]
print('window sizes: min', min(sizes), 'max', max(sizes))
print('slot 1 window:', pool_window[1][0], '->', pool_window[1][-1], len(pool_window[1]))
print('slot 60 window:', pool_window[60][0], '->', pool_window[60][-1], len(pool_window[60]))
print('slot 61 window:', pool_window[61][0], '->', pool_window[61][-1], len(pool_window[61]))
print('slot 366 window:', pool_window[366][0], '->', pool_window[366][-1], len(pool_window[366]))
need = []
d = dt.date(1991,12,27)
while d <= dt.date(2003,1,5):
    need.append(d); d += dt.timedelta(days=1)
print('needed days:', len(need), 'all present in union:', all(x in allw for x in need))
os.makedirs('/work/work', exist_ok=True)
with open('/work/work/pool_window.json','w') as f:
    json.dump({str(s): [x.isoformat() for x in pool_window[s]] for s in range(1,367)}, f)
print('saved pool_window.json')
