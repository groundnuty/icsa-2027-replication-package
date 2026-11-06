import numpy as np

def cell_mhw_days(h):
    n = len(h)
    runs = []
    i = 0
    while i < n:
        if h[i]:
            j = i
            while j < n and h[j]:
                j += 1
            runs.append((i, j-1))
            i = j
        else:
            i += 1
    runs = [(s, e) for s, e in runs if e - s + 1 >= 5]
    events = []
    for s, e in runs:
        if events and s - events[-1][1] - 1 <= 2:
            events[-1] = (events[-1][0], e)
        else:
            events.append((s, e))
    days = np.zeros(n, dtype=bool)
    for s, e in events:
        days[s:e+1] = True
    return days, events

def H(s, n=92):
    a = np.zeros(n, bool)
    for i in s: a[i] = True
    return a

tests = [
    (H([0,1,2,3,4]),                     [(0,4)]),            # exactly 5 at start
    (H([0,1,2,3]),                       []),                 # 4 -> none
    (H([0,1,2,3,4])|H([7,8,9,10,11]),    [(0,11)]),           # gap 2 -> join (len 12)
    (H([0,1,2,3,4])|H([8,9,10,11,12]),   [(0,4),(8,12)]),     # gap 3 -> no join
    (H([0,1,2,3,4])|H([6,7,8])|H([10,11,12,13,14]), [(0,4),(10,14)]),  # middle run <5
    (H([0,1,2,3,4])|H([7,8,9,10,11])|H([14,15,16,17,18]), [(0,18)]),   # cascade
    (H([87,88,89,90,91]),                [(87,91)]),          # at end
    (H(range(9))|H([10,14,15,16,17,18]), [(0,18)]),           # gap1 join, len: 9 + ... 
]
# fix last expected: hot 0..8, then 10,14..18: runs [0,8],[10,10]x? no: 10 alone (len1) & 14-18 (len5)
# rebuild that test properly
tests[-1] = (H(list(range(9)) + [14,15,16,17,18]), [(0,18)])  # runs [0,8] and [14,18], gap 5 -> no join
ok = True
for h, exp in tests:
    days, evs = cell_mhw_days(h)
    st = days.sum()
    e2 = sorted(evs)
    status = "OK" if e2 == exp else "FAIL"
    if status == "FAIL": ok = False
    print(f"n={h.sum():3d} events={e2} expected={exp} -> {status} (mhw days={st})")

# regional: active days -> maximal runs
def active_events(active):
    evs = []; i = 0
    while i < len(active):
        if active[i]:
            j = i
            while j < len(active) and active[j]: j += 1
            evs.append((i, j-1)); i = j
        else:
            i += 1
    return evs
a = np.zeros(20, bool); a[0:5]=True; a[7:12]=True; a[19]=True
print("active events:", active_events(a), "expected [(0,4),(7,11),(19,19)]")
print("ALL OK" if ok else "FAILURES PRESENT")
