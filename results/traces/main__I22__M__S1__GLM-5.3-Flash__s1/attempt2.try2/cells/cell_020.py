import datetime as dt, calendar, json, os
# doy_map: date -> day-of-year numbering 1..366 (1Jan=1, 28Feb=59, 29Feb=60, 1Mar=61, 31Dec=366)
def doy_map(d):
    k = d.timetuple().tm_yday
    if calendar.isleap(d.year):
        return k
    return k if k <= 59 else k + 1
# CORRECT exhaustive verification: build md->doy from leap year 2004; check all dates of many years
md2doy = {}
day = 0
for m in range(1, 13):
    for dd in range(1, calendar.monthrange(2004, m)[1] + 1):
        day += 1
        md2doy[(m, dd)] = day
allok = True
for y in range(1992, 2005):
    d = dt.date(y, 1, 1)
    while d.year == y:
        if doy_map(d) != md2doy[(d.month, d.day)]:
            print('MISMATCH', d, doy_map(d), md2doy[(d.month, d.day)]); allok = False
        d += dt.timedelta(days=1)
print('doy_map verified for 1992-2004:', allok)
# anchors grouped by mapped doy over baseline 1992-2002
slot_anchors = {}
for y in range(1992, 2003):
    d = dt.date(y, 1, 1)
    while d.year == y:
        slot_anchors.setdefault(doy_map(d), []).append(d)
        d += dt.timedelta(days=1)
print('slots with anchors:', len(slot_anchors), '| slot 60 anchors:', slot_anchors.get(60, []))
pool_window = {}
for s in range(1, 367):
    w = set()
    for d0 in slot_anchors.get(s, []):
        for off in range(-5, 6):
            w.add(d0 + dt.timedelta(days=off))
    pool_window[s] = sorted(w)
allw = set()
for s in range(1, 367): allw.update(pool_window[s])
print('union range:', min(allw), '->', max(allw), '| distinct days:', len(allw))
sizes = [len(pool_window[s]) for s in range(1, 367)]
print('window sizes: min', min(sizes), 'max', max(sizes))
for s in [1, 2, 59, 60, 61, 153, 244, 365, 366]:
    w = pool_window[s]
    print(f'slot {s}: {w[0]} -> {w[-1]}  n={len(w)}')
need = []
d = dt.date(1991, 12, 27)
while d <= dt.date(2003, 1, 5):
    need.append(d); d += dt.timedelta(days=1)
print('needed days:', len(need), '| all present in union:', all(x in allw for x in need))
with open('/work/work/pool_window.json', 'w') as f:
    json.dump({str(s): [x.isoformat() for x in pool_window[s]] for s in range(1, 367)}, f)
print('saved pool_window.json:', os.path.exists('/work/work/pool_window.json'))
