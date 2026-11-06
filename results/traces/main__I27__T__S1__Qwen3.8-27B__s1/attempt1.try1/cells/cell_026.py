
import numpy as np

hot = np.load('/tmp/mhw/hot.npy')   # (92, 3600)
sea2 = np.load('/tmp/mhw/sea2.npy')
NT, NC = hot.shape

def runs_of(h):
    # maximal True runs as (start, end) inclusive
    r = []
    i = 0
    n = len(h)
    while i < n:
        if h[i]:
            j = i
            while j+1 < n and h[j+1]:
                j += 1
            r.append([i, j])
            i = j+1
        else:
            i += 1
    return r

maskA = np.zeros((NT, NC), dtype=bool)
maskB = np.zeros((NT, NC), dtype=bool)
diff_cells = 0
ambiguous = 0   # cells where the two variants give different masks
for c in np.where(sea2)[0]:
    h = hot[:, c]
    if not h.any():
        continue
    runs = runs_of(h)
    mhws = [r for r in runs if r[1]-r[0]+1 >= 5]
    if not mhws:
        continue
    # variant A: gap in days <= 2
    mA = [list(mhws[0])]
    for r in mhws[1:]:
        if r[0] - mA[-1][1] - 1 <= 2:
            mA[-1][1] = r[1]
        else:
            mA.append(list(r))
    # variant B: non-hot days between <= 2
    mB = [list(mhws[0])]
    for r in mhws[1:]:
        between = slice(mB[-1][1]+1, r[0])
        nh = int((~h[between]).sum())
        if 1 <= nh <= 2:
            mB[-1][1] = r[1]
        else:
            mB.append(list(r))
    if mA != mB:
        diff_cells += 1
        ambiguous += 1
        print("DIFF cell", c, "mA:", mA, "mB:", mB)
    for s,e in mA: maskA[:, c] |= np.zeros(1, dtype=bool)  # placeholder
    for s,e in mA:
        maskA[s:e+1, c] = True
    for s,e in mB:
        maskB[s:e+1, c] = True

print("cells with different masks (A vs B):", diff_cells)
print("maskA MHW-days:", int(maskA.sum()), " maskB MHW-days:", int(maskB.sum()))
np.save('/tmp/mhw/maskA.npy', maskA)
np.save('/tmp/mhw/maskB.npy', maskB)
