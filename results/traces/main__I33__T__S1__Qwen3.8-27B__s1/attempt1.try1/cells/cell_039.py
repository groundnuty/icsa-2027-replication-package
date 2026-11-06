
import numpy as np, pickle
M = np.load('/work/work/M.npy')
hot = np.load('/work/work/hot.npy')
with open('/work/work/dates.pkl','rb') as f: D = pickle.load(f)
target_dates, sea = D['target'], D['sea']
n = M.shape[1]

def runs_of(b):
    out = []; i = 0
    while i < len(b):
        if b[i]:
            j = i
            while j+1 < len(b) and b[j+1]: j += 1
            out.append((i,j)); i = j+1
        else: i += 1
    return out

# 1) initial runs of >=5 hot days must be subset of M
viol1 = 0
for j in range(n):
    for (a,b) in runs_of(hot[:,j]):
        if b-a+1 >= 5 and not np.all(M[a:b+1,j]): viol1 += 1
print("initial runs not fully in M:", viol1)

# 2) every non-hot day inside M must be a join gap: hot day within 2 on both sides
viol2 = 0
for j in range(n):
    for k in range(92):
        if M[k,j] and not hot[k,j]:
            L = any(hot[max(0,k-2):k+1, j]); R = any(hot[k+1:min(92,k+3), j])
            if not (L and R): viol2 += 1
print("gap days lacking hot within 2 both sides:", viol2)

# 3) fixed-point: no pair of M-runs in a cell separated by <=2 non-M days
viol3 = 0
for j in range(n):
    rr = runs_of(M[:,j])
    for x in range(len(rr)-1):
        if rr[x+1][0] - rr[x][1] - 1 <= 2: viol3 += 1
print("M-runs with gap<=2:", viol3)

# 4) no M outside a cell's first..last MHW: M equals exactly union of joined runs (recompute independently)
def mhw_ref(h):
    Dn = len(h)
    res = [False]*Dn
    r0 = []
    i = 0
    while i < Dn:
        if h[i]:
            j = i
            while j+1 < Dn and h[j+1]: j += 1
            if j-i+1 >= 5: r0.append((i,j))
            i = j+1
        else: i += 1
    # merge
    merged = []
    for (a,b) in r0:
        if merged and a - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a,b))
    for (a,b) in merged:
        for k in range(a,b+1): res[k] = True
    return np.array(res)

mismatch = 0
for j in range(n):
    ref = mhw_ref(hot[:,j])
    if not np.array_equal(ref, M[:,j]): mismatch += 1
print("cells where independent recompute differs:", mismatch)

# cell 0 detail
j = 0
print("cell 0 hot :", ''.join('#' if hot[k,j] else ('.' if M[k,j] else '-') for k in range(92)))
rr_h = runs_of(hot[:,j]); rr_m = runs_of(M[:,j])
print("cell 0 hot runs (>=5):", [(a,b) for (a,b) in rr_h if b-a+1>=5], " all hot runs:", rr_h)
print("cell 0 M runs:", rr_m)
print("cell 0 M start/end dates:", target_dates[rr_m[0][0]], target_dates[rr_m[-1][1]])
