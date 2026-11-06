import datetime as dt, calendar, numpy as np
# doy numbering helpers (Feb29=60 numbering)
def doy_map(d):
    k = d.timetuple().tm_yday
    if calendar.isleap(d.year):
        return k
    return k if k <= 59 else k + 1
# slot -> set of dates in its pool window (sliding +-5 days around anchors)
slot_anchors = {}
for y in range(1992, 2003):
    d = dt.date(y, 1, 1)
    while d.year == y:
        slot_anchors.setdefault(doy_map(d), []).append(d)
        d += dt.timedelta(days=1)
pool_window = {}
for s in range(1, 367):
    w = set()
    for d0 in slot_anchors.get(s, []):
        for off in range(-5, 6):
            w.add(d0 + dt.timedelta(days=off))
    pool_window[s] = w
# For each needed calendar date (1991-12-27..2003-01-05), which pools include it?
member_of = {d: [] for d in pool_window.values() for d in d}  # all dates in union
all_dates = sorted(set().union(*pool_window.values()))
member_of = {d: [] for d in all_dates}
for s in range(1, 367):
    for d in pool_window[s]:
        member_of[d].append(s)
counts = [len(v) for v in member_of.values()]
print('pools per date: min', min(counts), 'max', max(counts))
print('date 1996-02-29 -> pools:', member_of[dt.date(1996,2,29)])
print('date 1992-02-29 -> pools:', member_of[dt.date(1992,2,29)])
# example: date 1992-06-15 (slot 167): should be in pools 162..172
mid = dt.date(1992, 6, 15)
print('date 1992-06-15 -> pools:', member_of[mid], '(expect 162..172)')
# check a window against naive re-derivation for one slot, e.g. slot 153 (June 2 anchor)
s = 153
naive = set()
for d0 in slot_anchors[s]:
    for off in range(-5, 6):
        naive.add(d0 + dt.timedelta(days=off))
print('slot', s, 'pool size', len(pool_window[s]), 'anchor doys:', [doy_map(x) for x in slot_anchors[s]])
