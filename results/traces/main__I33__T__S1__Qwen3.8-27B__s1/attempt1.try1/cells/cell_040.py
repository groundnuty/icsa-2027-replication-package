
import numpy as np
M = np.load('/work/work/M.npy')
hot = np.load('/work/work/hot.npy')
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

def mhw_ref(h):
    Dn = len(h)
    res = np.zeros(Dn, bool)
    r0 = []; i = 0
    while i < Dn:
        if h[i]:
            j = i
            while j+1 < Dn and h[j+1]: j += 1
            if j-i+1 >= 5: r0.append((i,j))
            i = j+1
        else: i += 1
    merged = []
    for (a,b) in r0:
        if merged and a - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a,b))
    for (a,b) in merged:
        res[a:b+1] = True
    return res

diff_cells = [j for j in range(n) if not np.array_equal(mhw_ref(hot[:,j]), M[:,j])]
print("n diff cells:", len(diff_cells))
j = diff_cells[0]
print("cell", j)
print("hot:", ''.join('#' if hot[k,j] else ('.' if M[k,j] else '-') for k in range(92)))
print("ref:", ''.join('#' if mhw_ref(hot[:,j])[k] else '-' for k in range(92)))
print("M  :", ''.join('#' if M[k,j] else '.' for k in range(92)))
print("hot runs:", runs_of(hot[:,j]))
print("M runs:", runs_of(M[:,j]))
print("ref runs:", runs_of(mhw_ref(hot[:,j])))
d = np.where(mhw_ref(hot[:,j]) != M[:,j])[0]
print("diff positions:", d, "hot there:", hot[d, j], "M there:", M[d, j])
