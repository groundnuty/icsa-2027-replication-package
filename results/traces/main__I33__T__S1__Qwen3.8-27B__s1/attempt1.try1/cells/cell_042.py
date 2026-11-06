
import numpy as np

def runs_of(b):
    out = []; i = 0
    while i < len(b):
        if b[i]:
            j = i
            while j+1 < len(b) and b[j+1]: j += 1
            out.append((i,j)); i = j+1
        else: i += 1
    return out

def mhw_a(hcol):
    Dn = len(hcol)
    r0 = [(a,b) for (a,b) in runs_of(hcol) if b-a+1 >= 5]
    merged = []
    for r in r0:
        if merged:
            gap = list(range(merged[-1][1]+1, r[0]))
            if len(gap) in (1,2) and not any(hcol[k] for k in gap):
                merged[-1] = (merged[-1][0], r[1])
            else:
                merged.append(r)
        else:
            merged.append(r)
    res = np.zeros(Dn, bool)
    for (a,b) in merged: res[a:b+1] = True
    return res, merged

# synthetic tests
T = [
 ( [1,1,1,1,1, 0, 1,1,1,1,1], (0,10), "gap1 nonhot -> merge" ),
 ( [1,1,1,1,1, 0,0, 1,1,1,1,1], (0,11), "gap2 nonhot -> merge" ),
 ( [1,1,1,1,1, 0,0,0, 1,1,1,1,1], [(0,4),(8,12)], "gap3 -> no merge" ),
 ( [1,1,1,1,1, 0,1, 1,1,1,1,1], [(0,4),(6,11)], "gap [nh,h] -> no merge" ),
 ( [1,1,1,1,1, 1, 1,1,1,1,1], (0,10), "no gap" ),
 ( [1,1,1,1, 0, 1,1,1,1,1], [(4,9)], "4-run not MHW; 5-run is" ),
 ( [1,1,1,1,1, 0, 1, 0, 1,1,1,1,1], (0,12), "chain: gap1+gap1 merges all (nh h nh: h in middle! wait)" ),
]
# note last: days: 0-4 run, 5 nh, 6 h, 7 nh, 8-12 run -> middle has hot day 6 -> per (a) NO merge!
for h, expected, desc in T:
    res, merged = mhw_a(np.array(h, bool))
    exp_mask = np.zeros(len(h), bool)
    for (a,b) in (expected if isinstance(expected, list) else [expected]):
        exp_mask[a:b+1] = True
    ok = np.array_equal(res, exp_mask)
    print(("PASS" if ok else "FAIL"), desc, "-> merged:", merged)
# fix expectation for last case per (a): no merge
h = np.array([1,1,1,1,1, 0, 1, 0, 1,1,1,1,1], bool)
res, merged = mhw_a(h)
print("chain case merged:", merged, "(expect [(0,4),(8,12)])", merged == [(0,4),(8,12)])
# true chain case: A,1nh,B,1nh,C
h = np.array([1,1,1,1,1, 0, 1,1,1,1,1, 0, 1,1,1,1,1], bool)
res, merged = mhw_a(h)
print("true chain:", merged, "expect [(0,16)]:", merged == [(0,16)])
